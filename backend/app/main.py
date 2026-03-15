from __future__ import annotations

import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.logging_setup import REQUEST_ID_CONTEXT, configure_logging
from app.schemas import SimulationRequest
from app.services.market_data import build_market_dataset
from app.services.simulation import (
    align_weekly_series,
    backtest_model,
    fit_pass_through_model,
    run_simulation,
)


LOGGER = configure_logging(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    RUNTIME_CACHE["loaded_at"] = 0.0
    RUNTIME_CACHE["payload"] = None
    RUNTIME_CACHE["observations"] = None
    LOGGER.info(
        "application_startup app=%s log_file=%s allowed_hosts=%s cors_origins=%s",
        settings.app_name,
        settings.log_file_path,
        settings.allowed_hosts,
        settings.cors_origins,
    )
    try:
        yield
    finally:
        LOGGER.info("application_shutdown app=%s", settings.app_name)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME_CACHE = {"loaded_at": 0.0, "payload": None, "observations": None}
RUNTIME_CACHE_LOCK = threading.Lock()


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request_path = request.url.path
    client_host = request.client.host if request.client else "-"
    started = time.perf_counter()
    token = REQUEST_ID_CONTEXT.set(request_id)
    LOGGER.info(
        "request_start method=%s path=%s client=%s",
        request.method,
        request_path,
        client_host,
    )
    try:
        response = await call_next(request)
    except Exception:
        LOGGER.exception(
            "request_failed method=%s path=%s client=%s",
            request.method,
            request_path,
            client_host,
        )
        REQUEST_ID_CONTEXT.reset(token)
        raise

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request_path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    LOGGER.info(
        "request_complete method=%s path=%s status=%s client=%s duration_ms=%s",
        request.method,
        request_path,
        response.status_code,
        client_host,
        elapsed_ms,
    )
    REQUEST_ID_CONTEXT.reset(token)
    return response


def _internal_error_response(message: str, *, action: str, exc: Exception) -> HTTPException:
    LOGGER.exception("%s error_type=%s", action, type(exc).__name__)
    detail = message
    if settings.expose_internal_error_details:
        detail = f"{message} {type(exc).__name__}: {exc}"
    return HTTPException(status_code=500, detail=detail)


def build_methodology_payload(mode: str, errors: list[str]) -> dict:
    return {
        "model_name": "Asymmetric weekly crude-to-gasoline pass-through model",
        "summary": (
            "The simulator estimates U.S. regular gasoline changes from lagged positive and negative WTI moves, "
            "a weekly error-correction term, and annual seasonality. The estimation window defaults to post-2018 "
            "weekly retail gasoline data to avoid the EIA survey break in the retail series."
        ),
        "assumptions": [
            "Weekly gasoline is the EIA U.S. regular all-formulations retail series.",
            "Weekly crude uses the average WTI spot close from the prior trading week and is aligned to the following Monday gasoline release.",
            "Positive and negative crude shocks are estimated separately so the model can capture asymmetric pass-through.",
            "Simulation scenarios move WTI linearly from the current weekly basis to the user-selected target over the selected transition window.",
        ],
        "sources": [
            {
                "name": "EIA Daily Prices",
                "url": "https://www.eia.gov/todayinenergy/prices.php",
                "description": "Current WTI close and U.S. average AAA retail gasoline, updated each weekday.",
            },
            {
                "name": "EIA Weekly Gasoline History",
                "url": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s=EMM_EPMR_PTE_NUS_DPG",
                "description": "Historical U.S. regular gasoline retail series used for the simulation model.",
            },
            {
                "name": "EIA WTI History",
                "url": "https://www.eia.gov/dnav/pet/hist/RWTCD.htm",
                "description": "Historical WTI spot prices used to build the weekly crude factor.",
            },
            {
                "name": "EIA Weekly Gasoline Page",
                "url": "https://www.eia.gov/petroleum/gasdiesel/",
                "description": "Release cadence and current component breakdown for the gasoline retail price.",
            },
            {
                "name": "NBER Working Paper 1992",
                "url": "https://www.nber.org/papers/w1992",
                "description": "Found that retail gasoline prices do not adjust symmetrically to crude oil price changes, which motivates the asymmetric lag structure.",
            },
        ],
        "mode": mode,
        "warnings": errors,
    }


def build_dashboard_payload(force_refresh: bool = False) -> tuple[dict, list[dict]]:
    with RUNTIME_CACHE_LOCK:
        now = time.time()
        if (
            not force_refresh
            and RUNTIME_CACHE["payload"] is not None
            and (now - RUNTIME_CACHE["loaded_at"]) < settings.cache_ttl_seconds
        ):
            LOGGER.info("dashboard_cache_hit age_seconds=%.2f", now - RUNTIME_CACHE["loaded_at"])
            return RUNTIME_CACHE["payload"], RUNTIME_CACHE["observations"]

        LOGGER.info("dashboard_cache_miss force_refresh=%s", force_refresh)
        dataset = build_market_dataset()
        observations = align_weekly_series(dataset["gasoline"], dataset["wti_weekly"])
        if len(observations) < 60:
            raise RuntimeError("Aligned weekly history is too short to drive the simulator.")

        model = fit_pass_through_model(observations)
        validation = backtest_model(observations)
        current = dataset["current"]
        latest_observation = observations[-1]

        daily_wti = current["wti_daily"]["value"]
        daily_gas = current["aaa_regular_gasoline"]["value"]
        crude_cost_per_gallon = daily_wti / 42.0
        eia_crude_share_reference = 0.495

        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "mode": dataset["mode"],
            "errors": dataset["errors"],
            "current": {
                "daily_wti": current["wti_daily"],
                "aaa_regular_gasoline": current["aaa_regular_gasoline"],
                "aaa_diesel": current.get("aaa_diesel"),
                "weekly_regular_gasoline": current["weekly_regular_gasoline"],
                "weekly_wti_for_model": current["weekly_wti_for_model"],
                "page_date": current["page_date"],
                "spot_close_date": current["spot_close_date"],
                "aaa_date": current["aaa_date"],
            },
            "calculator": {
                "defaults": {"miles": 300, "mpg": 26, "tank_gallons": 15},
                "daily_wti_per_gallon": round(crude_cost_per_gallon, 3),
                "daily_crude_share_of_pump": round(crude_cost_per_gallon / daily_gas, 3),
                "eia_reference_crude_share": eia_crude_share_reference,
            },
            "model": {
                "training_start": model["training_start"],
                "training_end": model["training_end"],
                "observations": len(model["observations"]),
                "lag_weeks": model["lags"],
                "long_run_beta": round(model["long_run"]["beta"], 4),
                "long_run_r_squared": round(model["long_run"]["r_squared"], 4),
                "short_run_r_squared": round(model["short_run"]["r_squared"], 4),
                "residual_std": round(model["short_run"]["residual_std"], 4),
                "validation_weeks": validation["weeks"],
                "validation_mae_cents": None if validation["mae"] is None else round(validation["mae"] * 100.0, 2),
                "validation_rmse_cents": None if validation["rmse"] is None else round(validation["rmse"] * 100.0, 2),
                "upside_pass_through_4w_cents_per_10_dollars": round(
                    sum(model["short_run"]["positive_coefficients"][:4]) * 10.0 * 100.0,
                    2,
                ),
                "downside_pass_through_8w_cents_per_10_dollars": round(
                    -sum(model["short_run"]["negative_coefficients"][:8]) * 10.0 * 100.0,
                    2,
                ),
            },
        "history": {
            "weekly_pairs": observations[-104:],
            "latest_basis": latest_observation,
        },
        "historical_event": {
            "label": "Iran war begins",
            "date": settings.iran_war_start_date,
        },
        "methodology": build_methodology_payload(dataset["mode"], dataset["errors"]),
        "diagnostics": {
            "log_file": str(settings.log_file_path) if settings.expose_source_diagnostics else None,
            "sources": list(dataset.get("diagnostics", {}).values()) if settings.expose_source_diagnostics else [],
        },
        }

        RUNTIME_CACHE["loaded_at"] = now
        RUNTIME_CACHE["payload"] = payload
        RUNTIME_CACHE["observations"] = observations
        LOGGER.info(
            "dashboard_payload_ready mode=%s errors=%s observations=%s",
            payload["mode"],
            len(payload["errors"]),
            len(observations),
        )
        return payload, observations


@app.get("/")
def root() -> dict:
    return {
        "app": settings.app_name,
        "docs_url": "/docs",
        "health_url": "/health",
        "dashboard_url": "/api/dashboard",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/dashboard")
def dashboard() -> dict:
    try:
        payload, _ = build_dashboard_payload()
        return payload
    except Exception as exc:
        raise _internal_error_response(
            "Failed to build dashboard payload.",
            action="dashboard_request_failed",
            exc=exc,
        ) from exc


@app.get("/api/refresh")
def refresh() -> dict:
    try:
        payload, _ = build_dashboard_payload(force_refresh=True)
        return payload
    except Exception as exc:
        raise _internal_error_response(
            "Failed to refresh dashboard payload.",
            action="refresh_request_failed",
            exc=exc,
        ) from exc


@app.post("/api/simulate")
def simulate(request: SimulationRequest) -> dict:
    if request.transition_weeks > request.horizon_weeks:
        raise HTTPException(
            status_code=400,
            detail="transition_weeks must be less than or equal to horizon_weeks.",
        )

    try:
        _, observations = build_dashboard_payload()
        return run_simulation(
            observations,
            request.target_wti,
            request.horizon_weeks,
            request.transition_weeks,
        )
    except Exception as exc:
        raise _internal_error_response(
            "Failed to run simulation.",
            action="simulation_request_failed",
            exc=exc,
        ) from exc

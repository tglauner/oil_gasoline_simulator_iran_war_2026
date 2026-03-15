from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import SimulationRequest
from app.services.market_data import build_market_dataset
from app.services.simulation import (
    align_weekly_series,
    backtest_model,
    fit_pass_through_model,
    run_simulation,
)


app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME_CACHE = {"loaded_at": 0.0, "payload": None, "observations": None}


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
    now = time.time()
    if (
        not force_refresh
        and RUNTIME_CACHE["payload"] is not None
        and (now - RUNTIME_CACHE["loaded_at"]) < settings.cache_ttl_seconds
    ):
        return RUNTIME_CACHE["payload"], RUNTIME_CACHE["observations"]

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
        "methodology": build_methodology_payload(dataset["mode"], dataset["errors"]),
    }

    RUNTIME_CACHE["loaded_at"] = now
    RUNTIME_CACHE["payload"] = payload
    RUNTIME_CACHE["observations"] = observations
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
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/refresh")
def refresh() -> dict:
    try:
        payload, _ = build_dashboard_payload(force_refresh=True)
        return payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
        raise HTTPException(status_code=500, detail=str(exc)) from exc

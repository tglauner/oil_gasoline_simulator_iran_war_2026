from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from pathlib import Path


def _parse_csv_env(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_bool_env(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_date_env(name: str, default: str) -> str:
    return dt.date.fromisoformat(os.getenv(name, default)).isoformat()


@dataclass(frozen=True)
class Settings:
    app_name: str
    cache_ttl_seconds: int
    cors_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    log_level: str
    truncate_logs_on_startup: bool
    log_dir: Path
    log_file_path: Path
    expose_source_diagnostics: bool
    expose_internal_error_details: bool
    source_fetch_timeout_seconds: float
    trump_administration_start_date: str
    iran_war_start_date: str


BACKEND_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BACKEND_DIR / "logs"


settings = Settings(
    app_name="Oil Gasoline Simulator Iran War 2026 API",
    cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "1800")),
    cors_origins=_parse_csv_env(
        os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    ),
    allowed_hosts=_parse_csv_env(os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")),
    log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    truncate_logs_on_startup=_parse_bool_env(os.getenv("TRUNCATE_LOGS_ON_STARTUP"), True),
    log_dir=LOG_DIR,
    log_file_path=LOG_DIR / "app.log",
    expose_source_diagnostics=_parse_bool_env(os.getenv("EXPOSE_SOURCE_DIAGNOSTICS"), True),
    expose_internal_error_details=_parse_bool_env(
        os.getenv("EXPOSE_INTERNAL_ERROR_DETAILS"),
        False,
    ),
    source_fetch_timeout_seconds=float(os.getenv("SOURCE_FETCH_TIMEOUT_SECONDS", "40")),
    trump_administration_start_date=_parse_date_env("TRUMP_ADMINISTRATION_START_DATE", "2025-01-20"),
    iran_war_start_date=_parse_date_env("IRAN_WAR_START_DATE", "2026-02-28"),
)

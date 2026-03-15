from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_csv_env(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str
    cache_ttl_seconds: int
    cors_origins: tuple[str, ...]


settings = Settings(
    app_name="Oil Gasoline Simulator Iran War 2026 API",
    cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "1800")),
    cors_origins=_parse_csv_env(
        os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173")
    ),
)

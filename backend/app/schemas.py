from __future__ import annotations

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    target_wti: float = Field(..., gt=0)
    horizon_weeks: int = Field(default=8, ge=1, le=26)
    transition_weeks: int = Field(default=2, ge=1, le=26)

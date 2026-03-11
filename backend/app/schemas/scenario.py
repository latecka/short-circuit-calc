"""Scenario schemas for API requests/responses."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScenarioCreate(BaseModel):
    """Schema for creating a new scenario."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    calculation_mode: str = Field("max", pattern="^(max|min)$")
    element_states: dict[str, dict[str, bool]] = Field(default_factory=dict)
    copy_from: Optional[str] = None  # scenario_id to copy element_states from


class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    calculation_mode: Optional[str] = Field(None, pattern="^(max|min)$")
    element_states: Optional[dict[str, dict[str, bool]]] = None


class ScenarioResponse(BaseModel):
    """Schema for scenario response."""
    id: str
    project_id: str
    name: str
    description: Optional[str]
    calculation_mode: str
    element_states: dict[str, dict[str, bool]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """Schema for list of scenarios."""
    items: list[ScenarioResponse]
    total: int


class ScenarioRunRequest(BaseModel):
    """Schema for running calculation with a scenario."""
    fault_types: list[str] = Field(..., min_length=1)
    fault_buses: Optional[list[str]] = None  # If None, use all buses


class ScenarioRunResponse(BaseModel):
    """Schema for scenario run response."""
    run_id: str
    scenario_id: str
    status: str
    message: str

"""Calculation run and result schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CalculationModeEnum(str, Enum):
    """Calculation mode."""
    MAX = "max"
    MIN = "min"


class FaultTypeEnum(str, Enum):
    """Fault type."""
    IK3 = "Ik3"
    IK2 = "Ik2"
    IK1 = "Ik1"


class CalculationStatusEnum(str, Enum):
    """Calculation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Request schemas
class CalculationRequest(BaseModel):
    """Request to run a calculation."""
    network_version_id: str
    calculation_mode: CalculationModeEnum = CalculationModeEnum.MAX
    fault_types: list[FaultTypeEnum] = Field(
        default=[FaultTypeEnum.IK3, FaultTypeEnum.IK2, FaultTypeEnum.IK1]
    )
    fault_buses: list[str] = Field(
        ..., min_length=1, description="List of bus IDs for fault locations"
    )


# Impedance schema
class ImpedanceSchema(BaseModel):
    """Complex impedance schema."""
    r: float
    x: float


# Result schemas
class RunResultResponse(BaseModel):
    """Single result for a bus and fault type."""
    id: str
    bus_id: str
    fault_type: FaultTypeEnum
    Ik: float = Field(..., description="Initial short-circuit current [kA]")
    ip: float = Field(..., description="Peak current [kA]")
    R_X_ratio: float
    c_factor: float
    Zk: ImpedanceSchema
    Z1: ImpedanceSchema
    Z2: ImpedanceSchema
    Z0: ImpedanceSchema | None = None
    correction_factors: dict[str, Any] = {}
    warnings: list[str] = []
    assumptions: list[str] = []

    model_config = {"from_attributes": True}


class CalculationRunResponse(BaseModel):
    """Calculation run response."""
    id: str
    project_id: str
    network_version_id: str
    user_id: str
    calculation_mode: CalculationModeEnum
    fault_types: list[str]
    fault_buses: list[str]
    engine_version: str
    status: CalculationStatusEnum
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    result_count: int = 0

    model_config = {"from_attributes": True}


class CalculationRunDetailResponse(CalculationRunResponse):
    """Calculation run with full results."""
    results: list[RunResultResponse] = []


class CalculationListResponse(BaseModel):
    """Paginated calculation list."""
    items: list[CalculationRunResponse]
    total: int
    page: int
    page_size: int


# Summary schemas for reports
class BusSummary(BaseModel):
    """Summary of results for a single bus."""
    bus_id: str
    bus_name: str | None = None
    Un: float
    Ik3_max: float | None = None
    Ik3_min: float | None = None
    Ik2_max: float | None = None
    Ik2_min: float | None = None
    Ik1_max: float | None = None
    Ik1_min: float | None = None
    ip_max: float | None = None


class CalculationSummaryResponse(BaseModel):
    """Summary of calculation results."""
    run_id: str
    project_name: str
    version_number: int
    calculation_mode: CalculationModeEnum
    bus_summaries: list[BusSummary]
    completed_at: datetime

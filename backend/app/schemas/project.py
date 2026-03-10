"""Project and NetworkVersion schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Network element schemas (simplified for JSON storage)
class BusbarSchema(BaseModel):
    """Busbar element schema."""
    id: str
    type: str = "busbar"
    name: str | None = None
    Un: float = Field(..., gt=0, description="Nominal voltage [kV]")
    is_reference: bool = False


class ExternalGridSchema(BaseModel):
    """External grid element schema."""
    id: str
    type: str = "external_grid"
    name: str | None = None
    bus_id: str
    Sk_max: float = Field(..., gt=0, description="Max short-circuit power [MVA]")
    Sk_min: float = Field(..., gt=0, description="Min short-circuit power [MVA]")
    rx_ratio: float = Field(..., gt=0, description="R/X ratio")
    c_max: float = 1.1
    c_min: float = 1.0
    Z0_Z1_ratio: float = 1.0
    X0_X1_ratio: float = 1.0
    R0_X0_ratio: float | None = None


class LineSchema(BaseModel):
    """Line/cable element schema."""
    id: str
    type: str = "overhead_line"  # or "cable"
    name: str | None = None
    bus_from: str
    bus_to: str
    length: float = Field(..., gt=0, description="Length [km]")
    r1_per_km: float = Field(..., ge=0)
    x1_per_km: float = Field(..., gt=0)
    r0_per_km: float = Field(..., ge=0)
    x0_per_km: float = Field(..., gt=0)
    parallel_lines: int = 1
    in_service: bool = True


class Transformer2WSchema(BaseModel):
    """2-winding transformer schema."""
    id: str
    type: str = "transformer_2w"
    name: str | None = None
    bus_hv: str
    bus_lv: str
    Sn: float = Field(..., gt=0, description="Rated power [MVA]")
    Un_hv: float = Field(..., gt=0)
    Un_lv: float = Field(..., gt=0)
    uk_percent: float = Field(..., gt=0, lt=100)
    Pkr: float = Field(..., ge=0, description="Short-circuit losses [kW]")
    vector_group: str
    tap_position: float = 0.0
    neutral_grounding_hv: str = "isolated"
    neutral_grounding_lv: str = "isolated"
    in_service: bool = True


class NetworkElementsSchema(BaseModel):
    """Container for all network elements."""
    busbars: list[dict[str, Any]] = []
    external_grids: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    transformers_2w: list[dict[str, Any]] = []
    transformers_3w: list[dict[str, Any]] = []
    autotransformers: list[dict[str, Any]] = []
    generators: list[dict[str, Any]] = []
    motors: list[dict[str, Any]] = []
    psus: list[dict[str, Any]] = []
    impedances: list[dict[str, Any]] = []
    grounding_impedances: list[dict[str, Any]] = []


# Project metadata schema
class ProjectMetadata(BaseModel):
    """Project metadata fields."""
    client_name: str | None = None
    client_address: str | None = None
    contractor_name: str | None = None
    contractor_address: str | None = None
    author: str | None = None
    checker: str | None = None
    project_number: str | None = None
    project_location: str | None = None
    revision: str | None = None
    notes: str | None = None


# Project schemas
class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    pass


class ProjectUpdate(BaseModel):
    """Project update schema."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    # Metadata fields
    client_name: str | None = None
    client_address: str | None = None
    contractor_name: str | None = None
    contractor_address: str | None = None
    author: str | None = None
    checker: str | None = None
    project_number: str | None = None
    project_location: str | None = None
    revision: str | None = None
    notes: str | None = None


class ProjectResponse(ProjectBase):
    """Project response schema."""
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    version_count: int = 0
    # Metadata fields
    client_name: str | None = None
    client_address: str | None = None
    contractor_name: str | None = None
    contractor_address: str | None = None
    author: str | None = None
    checker: str | None = None
    project_number: str | None = None
    project_location: str | None = None
    revision: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Paginated project list response."""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


# NetworkVersion schemas
class NetworkVersionBase(BaseModel):
    """Base network version schema."""
    comment: str | None = None


class NetworkVersionCreate(NetworkVersionBase):
    """Network version creation schema."""
    elements: dict[str, Any] = Field(default_factory=dict)


class NetworkVersionResponse(NetworkVersionBase):
    """Network version response schema."""
    id: str
    project_id: str
    version_number: int
    created_by_id: str
    created_at: datetime
    element_count: int = 0

    model_config = {"from_attributes": True}


class NetworkVersionDetailResponse(NetworkVersionResponse):
    """Network version with full elements."""
    elements: dict[str, Any]

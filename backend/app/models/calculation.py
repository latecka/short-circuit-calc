"""Calculation run and result models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import String, Text, DateTime, Float, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .user import User
    from .project import Project, NetworkVersion
    from .scenario import Scenario


class CalculationMode(str, Enum):
    """Calculation mode - max or min short-circuit."""
    MAX = "max"
    MIN = "min"


class CalculationStatus(str, Enum):
    """Calculation run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FaultType(str, Enum):
    """Fault type for short-circuit calculation."""
    IK3 = "Ik3"  # Three-phase fault
    IK2 = "Ik2"  # Two-phase fault
    IK1 = "Ik1"  # Single-phase to ground fault


class CalculationRun(Base):
    """Calculation run model - tracks a calculation execution."""

    __tablename__ = "calculation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), index=True
    )
    network_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("network_versions.id"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    scenario_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("scenarios.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Calculation parameters
    calculation_mode: Mapped[CalculationMode] = mapped_column(
        SQLEnum(CalculationMode), default=CalculationMode.MAX
    )
    fault_types: Mapped[list[str]] = mapped_column(
        JSON, default=list
    )  # List of fault types to calculate
    fault_buses: Mapped[list[str]] = mapped_column(
        JSON, default=list
    )  # List of bus IDs for fault locations

    # Execution metadata
    engine_version: Mapped[str] = mapped_column(String(50))
    input_hash: Mapped[str] = mapped_column(String(64))  # SHA-256 hash of input
    status: Mapped[CalculationStatus] = mapped_column(
        SQLEnum(CalculationStatus), default=CalculationStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="calculation_runs"
    )
    network_version: Mapped["NetworkVersion"] = relationship(
        "NetworkVersion", back_populates="calculation_runs"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="calculation_runs"
    )
    scenario: Mapped[Optional["Scenario"]] = relationship(
        "Scenario", back_populates="calculation_runs"
    )
    results: Mapped[list["RunResult"]] = relationship(
        "RunResult", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CalculationRun {self.id[:8]}... {self.status.value}>"


class RunResult(Base):
    """Calculation result for a single bus and fault type."""

    __tablename__ = "run_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("calculation_runs.id"), index=True
    )
    bus_id: Mapped[str] = mapped_column(String(255), index=True)
    fault_type: Mapped[FaultType] = mapped_column(SQLEnum(FaultType))

    # Results
    Ik: Mapped[float] = mapped_column(Float)  # Initial short-circuit current [kA]
    ip: Mapped[float] = mapped_column(Float)  # Peak current [kA]
    R_X_ratio: Mapped[float] = mapped_column(Float)  # R/X ratio at fault point
    c_factor: Mapped[float] = mapped_column(Float)  # Voltage factor used

    # Impedances stored as JSON: {"r": float, "x": float}
    Zk: Mapped[dict[str, float]] = mapped_column(JSON)  # Equivalent impedance
    Z1: Mapped[dict[str, float]] = mapped_column(JSON)  # Positive sequence
    Z2: Mapped[dict[str, float]] = mapped_column(JSON)  # Negative sequence
    Z0: Mapped[Optional[dict[str, float]]] = mapped_column(
        JSON, nullable=True
    )  # Zero sequence (if applicable)

    # Additional data
    correction_factors: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Relationship
    run: Mapped["CalculationRun"] = relationship(
        "CalculationRun", back_populates="results"
    )

    def __repr__(self) -> str:
        return f"<RunResult {self.bus_id} {self.fault_type.value}: Ik={self.Ik:.3f}kA>"

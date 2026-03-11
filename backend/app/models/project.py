"""Project and NetworkVersion models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Any

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .user import User
    from .calculation import CalculationRun
    from .scenario import Scenario


class Project(Base):
    """Project model - container for network versions."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Project metadata fields
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contractor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contractor_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    project_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    project_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    revision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    versions: Mapped[list["NetworkVersion"]] = relationship(
        "NetworkVersion", back_populates="project", cascade="all, delete-orphan",
        order_by="NetworkVersion.version_number"
    )
    calculation_runs: Mapped[list["CalculationRun"]] = relationship(
        "CalculationRun", back_populates="project", cascade="all, delete-orphan"
    )
    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario", back_populates="project", cascade="all, delete-orphan",
        order_by="Scenario.created_at"
    )

    @property
    def latest_version(self) -> Optional["NetworkVersion"]:
        """Get the latest network version."""
        if self.versions:
            return self.versions[-1]
        return None

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class NetworkVersion(Base):
    """Network version model - immutable snapshot of network elements."""

    __tablename__ = "network_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    elements: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )  # Stores all network elements as JSON
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="versions"
    )
    created_by: Mapped["User"] = relationship("User")
    calculation_runs: Mapped[list["CalculationRun"]] = relationship(
        "CalculationRun", back_populates="network_version"
    )

    def __repr__(self) -> str:
        return f"<NetworkVersion {self.project_id}:v{self.version_number}>"

"""User model for authentication."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .project import Project
    from .calculation import CalculationRun


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    calculation_runs: Mapped[list["CalculationRun"]] = relationship(
        "CalculationRun", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

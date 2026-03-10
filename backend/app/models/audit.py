"""Audit log model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .user import User


class AuditAction(str, Enum):
    """Audit action types."""
    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"

    # Project
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_DELETE = "project_delete"

    # Network Version
    VERSION_CREATE = "version_create"

    # Calculation
    CALCULATION_START = "calculation_start"
    CALCULATION_COMPLETE = "calculation_complete"
    CALCULATION_FAIL = "calculation_fail"
    CALCULATION_DELETE = "calculation_delete"

    # Export
    EXPORT_PDF = "export_pdf"
    EXPORT_XLSX = "export_xlsx"


class AuditLog(Base):
    """Audit log entry."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction))
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Relationship
    user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action.value} by {self.user_id}>"

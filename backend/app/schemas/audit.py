"""Audit log schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.audit import AuditAction


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: str
    user_id: str | None
    action: AuditAction
    resource_type: str | None
    resource_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    """Paginated audit log list."""
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int

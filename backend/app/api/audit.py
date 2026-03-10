"""Audit log API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import DBSession, SuperUser
from app.models import AuditLog, AuditAction
from app.schemas.audit import AuditLogResponse, AuditListResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
def list_audit_logs(
    db: DBSession,
    current_user: SuperUser,  # Only superusers can view audit logs
    user_id: str | None = None,
    action: AuditAction | None = None,
    resource_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List audit log entries (superuser only)."""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if from_date:
        query = query.filter(AuditLog.created_at >= from_date)
    if to_date:
        query = query.filter(AuditLog.created_at <= to_date)

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return AuditListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/my", response_model=AuditListResponse)
def list_my_audit_logs(
    db: DBSession,
    current_user: SuperUser,
    action: AuditAction | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List current user's audit logs."""
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)

    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return AuditListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )

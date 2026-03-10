"""Audit logging service."""

from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, AuditAction


def log_action(
    db: Session,
    action: AuditAction,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Log an audit action."""
    ip_address = None
    user_agent = None

    if request:
        # Get client IP (handle proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        user_agent = request.headers.get("User-Agent")

    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return log_entry


def log_login(db: Session, user_id: str, request: Optional[Request] = None) -> AuditLog:
    """Log successful login."""
    return log_action(
        db,
        AuditAction.LOGIN,
        user_id=user_id,
        resource_type="user",
        resource_id=user_id,
        request=request,
    )


def log_project_action(
    db: Session,
    action: AuditAction,
    user_id: str,
    project_id: str,
    project_name: str,
    request: Optional[Request] = None,
) -> AuditLog:
    """Log project-related action."""
    return log_action(
        db,
        action,
        user_id=user_id,
        resource_type="project",
        resource_id=project_id,
        details={"project_name": project_name},
        request=request,
    )


def log_calculation_action(
    db: Session,
    action: AuditAction,
    user_id: str,
    run_id: str,
    project_id: str,
    details: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Log calculation-related action."""
    return log_action(
        db,
        action,
        user_id=user_id,
        resource_type="calculation",
        resource_id=run_id,
        details={"project_id": project_id, **(details or {})},
        request=request,
    )

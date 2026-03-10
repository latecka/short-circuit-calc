"""Export API endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession, CurrentUser
from app.models import CalculationRun, Project, NetworkVersion, AuditAction
from app.services import export_pdf, export_xlsx
from app.services.audit import log_action

router = APIRouter(prefix="/export", tags=["export"])


def _get_calculation_data(db: DBSession, run_id: str, current_user: CurrentUser):
    """Get calculation run with project and version data."""
    run = db.query(CalculationRun).filter(
        CalculationRun.id == run_id,
        CalculationRun.user_id == current_user.id,
    ).first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found",
        )

    project = db.query(Project).filter(Project.id == run.project_id).first()
    version = db.query(NetworkVersion).filter(NetworkVersion.id == run.network_version_id).first()

    return run, project, version


@router.get("/pdf/{run_id}")
def export_pdf_report(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Export calculation results as PDF."""
    run, project, version = _get_calculation_data(db, run_id, current_user)

    # Generate PDF
    pdf_buffer = export_pdf.generate_calculation_report(run, project, version)

    # Log export
    log_action(
        db,
        AuditAction.EXPORT_PDF,
        user_id=current_user.id,
        resource_type="calculation",
        resource_id=run_id,
        details={"project_name": project.name},
    )

    # Create filename
    filename = f"skrat_{project.name.replace(' ', '_')}_v{version.version_number}_{run.calculation_mode.value}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/xlsx/{run_id}")
def export_xlsx_report(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Export calculation results as XLSX."""
    run, project, version = _get_calculation_data(db, run_id, current_user)

    # Generate XLSX
    xlsx_buffer = export_xlsx.generate_calculation_report(run, project, version)

    # Log export
    log_action(
        db,
        AuditAction.EXPORT_XLSX,
        user_id=current_user.id,
        resource_type="calculation",
        resource_id=run_id,
        details={"project_name": project.name},
    )

    # Create filename
    filename = f"skrat_{project.name.replace(' ', '_')}_v{version.version_number}_{run.calculation_mode.value}.xlsx"

    return StreamingResponse(
        xlsx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

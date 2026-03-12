"""Export API endpoints."""

from io import BytesIO

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse, Response

from app.api.deps import DBSession, CurrentUser
from app.models import CalculationRun, Project, NetworkVersion, Scenario, AuditAction
from app.services import export_pdf, export_xlsx
from app.services.network_schema import generate_network_schema
from app.services.audit import log_action

router = APIRouter(prefix="/export", tags=["export"])


def _get_calculation_data(db: DBSession, run_id: str, current_user: CurrentUser):
    """Get calculation run with project, version and scenario data."""
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

    # Get scenario if linked
    scenario = None
    if run.scenario_id:
        scenario = db.query(Scenario).filter(Scenario.id == run.scenario_id).first()

    return run, project, version, scenario


@router.get("/pdf/{run_id}")
def export_pdf_report(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Export calculation results as PDF."""
    run, project, version, scenario = _get_calculation_data(db, run_id, current_user)

    # Generate PDF
    pdf_buffer = export_pdf.generate_calculation_report(run, project, version, scenario)

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
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/xlsx/{run_id}")
def export_xlsx_report(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Export calculation results as XLSX."""
    run, project, version, scenario = _get_calculation_data(db, run_id, current_user)

    # Generate XLSX
    xlsx_buffer = export_xlsx.generate_calculation_report(run, project, version, scenario)

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
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/schema/{run_id}")
def export_network_schema_endpoint(
    run_id: str,
    db: DBSession,
    current_user: CurrentUser,
    format: str = Query("svg", pattern="^(svg|png)$"),
):
    """Export network schema as SVG or PNG diagram."""
    run, project, version, scenario = _get_calculation_data(db, run_id, current_user)

    # Get network elements
    elements = version.elements or {}

    # Get results for display on diagram
    results = None
    if run.results:
        results = [
            {
                'bus_id': r.bus_id,
                'fault_type': r.fault_type.value,
                'Ik': r.Ik,
                'ip': r.ip,
            }
            for r in run.results
        ]

    # Get element active checker from scenario for proper visualization
    is_active_fn = scenario.is_element_active if scenario else None

    # Generate schema
    schema_bytes = generate_network_schema(
        elements=elements,
        results=results,
        format=format,
        is_element_active_fn=is_active_fn,
    )

    # Determine media type
    media_type = "image/svg+xml" if format == "svg" else "image/png"

    # Create filename
    filename = f"schema_{project.name.replace(' ', '_')}_v{version.version_number}.{format}"

    return Response(
        content=schema_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/network/{project_id}")
def export_network_xlsx(
    project_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Export network elements as XLSX backup file."""
    # Check project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get latest version
    version = db.query(NetworkVersion).filter(
        NetworkVersion.project_id == project_id,
    ).order_by(NetworkVersion.version_number.desc()).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No network version found",
        )

    # Generate XLSX with network elements
    xlsx_buffer = export_xlsx.generate_network_backup(version.elements or {})

    # Log export
    log_action(
        db,
        AuditAction.EXPORT_XLSX,
        user_id=current_user.id,
        resource_type="project",
        resource_id=project_id,
        details={"project_name": project.name, "type": "network_backup"},
    )

    # Create filename
    from datetime import date
    filename = f"{project.name.replace(' ', '_')}_backup_{date.today().isoformat()}.xlsx"

    return StreamingResponse(
        xlsx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

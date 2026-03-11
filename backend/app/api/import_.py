"""Import API endpoints."""

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.api.deps import DBSession, CurrentUser
from app.models import Project, NetworkVersion
from app.services.import_network import (
    import_from_json,
    import_from_xlsx,
    generate_template_xlsx,
    ImportError,
)

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/json/{project_id}")
async def import_json(
    project_id: str,
    file: UploadFile = File(...),
    db: DBSession = None,
    current_user: CurrentUser = None,
):
    """
    Import network elements from JSON file.

    Creates a new network version with imported elements.
    """
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

    # Check file type
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON file",
        )

    try:
        content = await file.read()
        elements = import_from_json(content)
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(e),
                "errors": e.errors,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        )

    # Get next version number
    max_version = db.query(NetworkVersion).filter(
        NetworkVersion.project_id == project_id
    ).count()

    # Create new version
    version = NetworkVersion(
        project_id=project_id,
        version_number=max_version + 1,
        elements=elements,
        comment=f"Importované z {file.filename}",
        created_by_id=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # Count elements
    element_count = sum(len(v) for v in elements.values() if isinstance(v, list))

    return {
        "message": "Import successful",
        "version_id": version.id,
        "version_number": version.version_number,
        "element_count": element_count,
    }


@router.post("/xlsx/{project_id}")
async def import_xlsx(
    project_id: str,
    file: UploadFile = File(...),
    db: DBSession = None,
    current_user: CurrentUser = None,
):
    """
    Import network elements from XLSX file.

    Creates a new network version with imported elements.
    """
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

    # Check file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx)",
        )

    try:
        content = await file.read()
        elements = import_from_xlsx(content)
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(e),
                "errors": e.errors,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}",
        )

    # Get next version number
    max_version = db.query(NetworkVersion).filter(
        NetworkVersion.project_id == project_id
    ).count()

    # Create new version
    version = NetworkVersion(
        project_id=project_id,
        version_number=max_version + 1,
        elements=elements,
        comment=f"Importované z {file.filename}",
        created_by_id=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    # Count elements
    element_count = sum(len(v) for v in elements.values() if isinstance(v, list))

    return {
        "message": "Import successful",
        "version_id": version.id,
        "version_number": version.version_number,
        "element_count": element_count,
    }


@router.get("/template")
async def download_template():
    """Download XLSX template for import."""
    template = generate_template_xlsx()

    return StreamingResponse(
        BytesIO(template),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="network_template.xlsx"',
        },
    )


@router.get("/template/json")
async def download_template_json():
    """Download JSON template with sample data for import."""
    import json
    from fastapi.responses import JSONResponse

    # Sample data with realistic values
    sample_data = {
        "export_version": "1.0",
        "exported_at": "2026-01-01T00:00:00Z",
        "project": {
            "name": "Vzorový projekt",
            "description": "Vzorový projekt pre import"
        },
        "network_elements": {
            "busbars": [
                {"id": "BUS_110", "name": "Rozvodňa 110 kV", "Un": 110, "is_reference": True},
                {"id": "BUS_22", "name": "Rozvodňa 22 kV", "Un": 22, "is_reference": False},
                {"id": "BUS_0.4", "name": "Rozvodňa 0.4 kV", "Un": 0.4, "is_reference": False}
            ],
            "external_grids": [
                {
                    "id": "GRID_1",
                    "name": "Napájacia sústava",
                    "bus_id": "BUS_110",
                    "Sk_max": 5000,
                    "Sk_min": 4000,
                    "rx_ratio": 0.1,
                    "c_max": 1.1,
                    "c_min": 1.0
                }
            ],
            "lines": [
                {
                    "id": "LINE_1",
                    "name": "Vedenie VN 1",
                    "type": "overhead_line",
                    "bus_from": "BUS_22",
                    "bus_to": "BUS_22",
                    "length": 5.5,
                    "r1_per_km": 0.12,
                    "x1_per_km": 0.35,
                    "r0_per_km": 0.36,
                    "x0_per_km": 1.05,
                    "parallel_lines": 1,
                    "in_service": True
                },
                {
                    "id": "CABLE_1",
                    "name": "Kábel NN",
                    "type": "cable",
                    "bus_from": "BUS_0.4",
                    "bus_to": "BUS_0.4",
                    "length": 0.2,
                    "r1_per_km": 0.206,
                    "x1_per_km": 0.08,
                    "r0_per_km": 0.824,
                    "x0_per_km": 0.32,
                    "parallel_lines": 1,
                    "in_service": True
                }
            ],
            "transformers_2w": [
                {
                    "id": "TR_1",
                    "name": "Transformátor T1 110/22 kV",
                    "bus_hv": "BUS_110",
                    "bus_lv": "BUS_22",
                    "Sn": 40,
                    "Un_hv": 110,
                    "Un_lv": 22,
                    "uk_percent": 12.5,
                    "Pkr": 150,
                    "vector_group": "YNd11",
                    "tap_position": 0,
                    "neutral_grounding_hv": "grounded",
                    "neutral_grounding_lv": "isolated",
                    "in_service": True
                }
            ],
            "generators": [
                {
                    "id": "GEN_1",
                    "name": "Generátor G1",
                    "bus_id": "BUS_22",
                    "Sn": 10,
                    "Un": 22,
                    "Xd_pp": 15,
                    "Ra": 0.5,
                    "cos_phi": 0.85,
                    "connection": "direct",
                    "in_service": True
                }
            ],
            "motors": [],
            "transformers_3w": [],
            "autotransformers": [],
            "psus": [],
            "impedances": [],
            "grounding_impedances": []
        }
    }

    content = json.dumps(sample_data, indent=2, ensure_ascii=False)

    return StreamingResponse(
        BytesIO(content.encode('utf-8')),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="network_template.json"',
        },
    )


@router.post("/validate/json")
async def validate_json(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
):
    """
    Validate JSON file without importing.

    Returns validation results.
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON file",
        )

    try:
        content = await file.read()
        elements = import_from_json(content)
        element_count = sum(len(v) for v in elements.values() if isinstance(v, list))

        return {
            "valid": True,
            "element_count": element_count,
            "summary": {k: len(v) for k, v in elements.items() if v},
        }
    except ImportError as e:
        return {
            "valid": False,
            "message": str(e),
            "errors": e.errors,
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Failed to parse file: {str(e)}",
            "errors": [],
        }


@router.post("/validate/xlsx")
async def validate_xlsx(
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
):
    """
    Validate XLSX file without importing.

    Returns validation results.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx)",
        )

    try:
        content = await file.read()
        elements = import_from_xlsx(content)
        element_count = sum(len(v) for v in elements.values() if isinstance(v, list))

        return {
            "valid": True,
            "element_count": element_count,
            "summary": {k: len(v) for k, v in elements.items() if v},
        }
    except ImportError as e:
        return {
            "valid": False,
            "message": str(e),
            "errors": e.errors,
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Failed to parse file: {str(e)}",
            "errors": [],
        }

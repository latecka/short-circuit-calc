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

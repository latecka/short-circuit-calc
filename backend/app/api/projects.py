"""Projects API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DBSession, CurrentUser
from app.models import Project, NetworkVersion
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    NetworkVersionCreate,
    NetworkVersionResponse,
    NetworkVersionDetailResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _count_elements(elements: dict) -> int:
    """Count total elements in network."""
    count = 0
    for key, value in elements.items():
        if isinstance(value, list):
            count += len(value)
    return count


def _project_to_response(project: Project) -> ProjectResponse:
    """Convert Project model to response schema."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        version_count=len(project.versions),
    )


def _version_to_response(version: NetworkVersion, include_elements: bool = False):
    """Convert NetworkVersion model to response schema."""
    base = {
        "id": version.id,
        "project_id": version.project_id,
        "version_number": version.version_number,
        "comment": version.comment,
        "created_by_id": version.created_by_id,
        "created_at": version.created_at,
        "element_count": _count_elements(version.elements or {}),
    }
    if include_elements:
        return NetworkVersionDetailResponse(**base, elements=version.elements or {})
    return NetworkVersionResponse(**base)


# Project CRUD
@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List user's projects."""
    query = db.query(Project).filter(Project.owner_id == current_user.id)

    total = query.count()
    projects = (
        query.order_by(Project.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProjectListResponse(
        items=[_project_to_response(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new project."""
    project = Project(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get project by ID."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description

    db.commit()
    db.refresh(project)

    return _project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete project and all its versions."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    db.delete(project)
    db.commit()


# Network Versions
@router.get("/{project_id}/versions", response_model=list[NetworkVersionResponse])
def list_versions(
    project_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """List all versions of a project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return [_version_to_response(v) for v in project.versions]


@router.post(
    "/{project_id}/versions",
    response_model=NetworkVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    project_id: str,
    data: NetworkVersionCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Create a new network version."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get next version number
    max_version = (
        db.query(NetworkVersion)
        .filter(NetworkVersion.project_id == project_id)
        .count()
    )

    version = NetworkVersion(
        project_id=project_id,
        version_number=max_version + 1,
        elements=data.elements,
        comment=data.comment,
        created_by_id=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    return _version_to_response(version)


@router.get("/{project_id}/versions/{version_id}", response_model=NetworkVersionDetailResponse)
def get_version(
    project_id: str,
    version_id: str,
    db: DBSession,
    current_user: CurrentUser,
):
    """Get network version with full elements."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    version = db.query(NetworkVersion).filter(
        NetworkVersion.id == version_id,
        NetworkVersion.project_id == project_id,
    ).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    return _version_to_response(version, include_elements=True)

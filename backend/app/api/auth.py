"""Authentication API endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DBSession, CurrentUser
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import User
from app.schemas import Token, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: DBSession):
    """Register a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(
    db: DBSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Login and get access token."""
    # Find user by email (username field contains email)
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Create access token
    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: CurrentUser):
    """Get current user information."""
    return current_user


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: CurrentUser):
    """Refresh access token."""
    access_token = create_access_token(
        subject=current_user.id,
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token)

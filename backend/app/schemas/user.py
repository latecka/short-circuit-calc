"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: str | None = None
    password: str | None = None


class UserResponse(UserBase):
    """User response schema."""
    id: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """User in database (includes hashed password)."""
    hashed_password: str

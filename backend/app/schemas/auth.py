"""Authentication schemas."""

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str | None = None


class LoginRequest(BaseModel):
    """Login request body."""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    full_name: str | None = None

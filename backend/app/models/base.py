"""SQLAlchemy base model and utilities."""

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Naming conventions for constraints (required for Alembic)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = MetaData(naming_convention=convention)


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())

"""Database configuration and session management."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .core.config import settings
from .models import Base


# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite specific
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
    echo=settings.DEBUG,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

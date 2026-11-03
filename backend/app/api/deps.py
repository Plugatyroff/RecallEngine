"""Shared dependencies for the endpoints (FastAPI passes them in as function parameters)."""

from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


def get_session() -> Iterator[Session]:
    """One database session per request: committed if the request succeeds, rolled back if not."""
    with SessionLocal.begin() as session:
        yield session


def get_now() -> datetime:
    """The current time; tests replace this to control time."""
    return datetime.now(UTC)

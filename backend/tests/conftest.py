"""Shared test setup: a freshly migrated test database and a session per test.

conftest.py is loaded by pytest automatically; the fixtures defined here can be used by
any test simply by naming them as a function parameter.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import make_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Rebuild the test database from scratch once per test run, using the real migrations.

    Running downgrade and upgrade also checks that the migrations themselves work.
    """
    engine = make_engine(settings.test_db_name)
    alembic_config = Config(BACKEND_DIR / "alembic.ini")
    with engine.begin() as connection:
        alembic_config.attributes["connection"] = connection
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        yield connection


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    """A session whose changes are rolled back after each test, so tests never affect each other."""
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()

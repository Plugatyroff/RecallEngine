"""Alembic environment: tells Alembic which database to change and what the models look like."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

import app.models  # noqa: F401  (registers every table with Base.metadata)
from app.core.database import Base, make_engine
from app.core.types import UTCDateTime

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The models, which autogenerate compares against the real database.
target_metadata = Base.metadata


def render_item(type_: str, obj: object, autogen_context) -> str | bool:
    """Write UTCDateTime columns into migrations as plain DATETIME2.

    Migrations should describe the database itself, not depend on Python helper types
    that may change later.
    """
    if type_ == "type" and isinstance(obj, UTCDateTime):
        autogen_context.imports.add("from sqlalchemy.dialects import mssql")
        return "mssql.DATETIME2()"
    return False


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (alembic upgrade head --sql)."""
    context.configure(
        url=make_engine().url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests pass in their own connection to the test database; otherwise use the main one.
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return

    with make_engine(poolclass=pool.NullPool).connect() as connection:
        _run(connection)


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

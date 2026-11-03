"""Database connection and the base class for all table models."""

from typing import Any

from sqlalchemy import URL, Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Give every constraint and index a predictable name, so later migrations can find them.
# Without this, SQL Server generates random names like FK__cards__topic__3B75D760.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def database_url(db_name: str) -> URL:
    """Build the connection URL for a database on the configured SQL Server instance."""
    return URL.create(
        "mssql+pyodbc",
        host=settings.db_server,
        database=db_name,
        query={
            "driver": settings.db_driver,
            "trusted_connection": "yes",  # log in with the current Windows account
            "TrustServerCertificate": "yes",  # a local SQL Server uses a self-signed certificate
        },
    )


def make_engine(db_name: str = settings.db_name, **kwargs: Any) -> Engine:
    return create_engine(database_url(db_name), **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine)

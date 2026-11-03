"""Custom column types shared by the models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Dialect
from sqlalchemy.dialects import mssql
from sqlalchemy.types import TypeDecorator, TypeEngine


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """A timestamp that is always stored in UTC.

    SQL Server's DATETIME2 has no time zone, so values are converted to UTC before
    saving and marked as UTC again when loaded. Python code therefore always works
    with time-zone-aware datetimes and can never mix up local and UTC times.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[datetime]:
        if dialect.name == "mssql":
            return dialect.type_descriptor(mssql.DATETIME2())
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires a time-zone-aware datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)

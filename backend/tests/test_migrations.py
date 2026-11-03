from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from tests.conftest import BACKEND_DIR


def test_migrations_match_the_models(engine: Engine) -> None:
    """Fails if a model was changed without writing a migration for it."""
    alembic_config = Config(BACKEND_DIR / "alembic.ini")
    with engine.connect() as connection:
        alembic_config.attributes["connection"] = connection
        command.check(alembic_config)

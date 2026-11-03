"""Application settings, read from environment variables or the backend/.env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # SQL Server instance, e.g. "localhost\SQLEXPRESS". Connects with Windows authentication.
    db_server: str = r"localhost\SQLEXPRESS"
    db_name: str = "RecallEngine"
    # Database used by the automated tests; it is wiped on every test run.
    test_db_name: str = "RecallEngine_test"
    db_driver: str = "ODBC Driver 18 for SQL Server"
    # Folder for card media (images, audio). It is user data, so it lives outside the repository.
    media_dir: Path = Path.home() / "RecallEngine-data" / "media"


settings = Settings()

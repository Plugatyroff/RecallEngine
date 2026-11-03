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
    # User data lives outside the repository, in %USERPROFILE%\RecallEngine-data
    # Folder for card media (images, audio)
    media_dir: Path = Path.home() / "RecallEngine-data" / "media"
    # Anki files dropped into the inbox are imported automatically, then moved to anki-exports
    inbox_dir: Path = Path.home() / "RecallEngine-data" / "inbox"
    imported_dir: Path = Path.home() / "RecallEngine-data" / "anki-exports"
    # How often the backend checks the inbox, in seconds; 0 turns the automatic check off
    inbox_poll_seconds: float = 5


settings = Settings()

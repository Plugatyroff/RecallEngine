"""Tests for the inbox: Anki files dropped into a folder are imported automatically."""

import os
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Note
from app.services import inbox
from tests.test_anki_import import build_export


@pytest.fixture(autouse=True)
def folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    paths = {name: tmp_path / name for name in ("inbox", "imported", "media")}
    monkeypatch.setattr(settings, "inbox_dir", paths["inbox"])
    monkeypatch.setattr(settings, "imported_dir", paths["imported"])
    monkeypatch.setattr(settings, "media_dir", paths["media"])
    paths["inbox"].mkdir()
    return paths


def opener(session: Session):
    """What the inbox calls to get a session: here, the test session (rolled back after the test)."""
    @contextmanager
    def open_session():
        yield session
    return open_session


def drop(folder: Path, source: Path, name: str, age_seconds: float = 60) -> Path:
    """Put a file into the inbox, pretending it was last changed age_seconds ago."""
    target = folder / name
    target.write_bytes(source.read_bytes())
    old = time.time() - age_seconds
    os.utime(target, (old, old))
    return target


def test_a_dropped_deck_is_imported_and_moved(session: Session, tmp_path: Path, folders: dict[str, Path]) -> None:
    drop(folders["inbox"], build_export(tmp_path), "Hungarian.apkg")

    results = inbox.process_inbox(opener(session))

    assert [(r.file, r.imported) for r in results] == [("Hungarian.apkg", True)]
    assert session.scalar(select(Note).where(Note.anki_guid == "guid-alma")) is not None
    assert not (folders["inbox"] / "Hungarian.apkg").exists()
    assert (folders["imported"] / "Hungarian.apkg").exists()


def test_a_file_still_being_written_is_left_for_later(session: Session, tmp_path: Path, folders: dict[str, Path]) -> None:
    drop(folders["inbox"], build_export(tmp_path), "fresh.apkg", age_seconds=0)

    assert inbox.process_inbox(opener(session)) == []
    assert (folders["inbox"] / "fresh.apkg").exists()


def test_other_files_are_ignored(session: Session, folders: dict[str, Path]) -> None:
    (folders["inbox"] / "notes.txt").write_text("hello")

    assert inbox.process_inbox(opener(session)) == []


def test_a_broken_file_is_moved_aside_with_the_reason(session: Session, folders: dict[str, Path]) -> None:
    broken = folders["inbox"] / "broken.apkg"
    broken.write_text("not a zip")
    old = time.time() - 60
    os.utime(broken, (old, old))

    results = inbox.process_inbox(opener(session))

    assert [(r.file, r.imported) for r in results] == [("broken.apkg", False)]
    failed = folders["inbox"] / "failed"
    assert (failed / "broken.apkg").exists()
    assert "not an Anki export" in (failed / "broken.apkg.error.txt").read_text(encoding="utf-8")


def test_an_imported_file_never_overwrites_an_earlier_one(session: Session, tmp_path: Path, folders: dict[str, Path]) -> None:
    export = build_export(tmp_path)
    for _ in range(2):
        drop(folders["inbox"], export, "deck.apkg")
        inbox.process_inbox(opener(session))

    assert sorted(p.name for p in folders["imported"].iterdir()) == ["deck (2).apkg", "deck.apkg"]

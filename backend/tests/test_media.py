"""Tests for storing and serving media files."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import media
from app.services.errors import InvalidInputError, NotFoundError
from app.services.templates import render_sounds


@pytest.fixture(autouse=True)
def media_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Use an empty temporary media folder instead of the real one."""
    folder = tmp_path / "media"
    monkeypatch.setattr(settings, "media_dir", folder)
    yield folder


def test_a_file_is_stored_under_its_name(media_dir: Path) -> None:
    assert media.store("picture.jpg", b"jpg-bytes") == "picture.jpg"
    assert (media_dir / "picture.jpg").read_bytes() == b"jpg-bytes"


def test_storing_the_same_file_again_changes_nothing(media_dir: Path) -> None:
    media.store("picture.jpg", b"same")

    assert media.store("picture.jpg", b"same") == "picture.jpg"
    assert sorted(p.name for p in media_dir.iterdir()) == ["picture.jpg"]


def test_a_different_file_with_a_taken_name_gets_a_numbered_name(media_dir: Path) -> None:
    media.store("image.png", b"first deck")

    assert media.store("image.png", b"second deck") == "image (2).png"
    assert media.store("image.png", b"third deck") == "image (3).png"
    assert media.store("image.png", b"second deck") == "image (2).png"
    assert (media_dir / "image.png").read_bytes() == b"first deck"


@pytest.mark.parametrize("name", ["../secret.txt", "..\\secret.txt", "a/b.png", "C:x.png", ".hidden", "", ".."])
def test_names_that_could_point_elsewhere_are_rejected(name: str) -> None:
    with pytest.raises(InvalidInputError):
        media.store(name, b"x")


def test_a_missing_file_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        media.media_path("nothing.png")


def test_media_is_served_by_the_api() -> None:
    media.store("szőlő grapes.jpg", b"image")
    client = TestClient(app)

    response = client.get("/api/v1/media/sz%C5%91l%C5%91%20grapes.jpg")

    assert response.status_code == 200
    assert response.content == b"image"
    assert client.get("/api/v1/media/missing.jpg").status_code == 404
    assert client.get("/api/v1/media/..%5Csecret.txt").status_code == 404


def test_katex_files_are_served() -> None:
    client = TestClient(app)

    for path in ("katex.min.js", "katex.min.css", "contrib/auto-render.min.js", "render-math.js",
                 "fonts/KaTeX_Main-Regular.woff2"):
        assert client.get(f"/static/katex/{path}").status_code == 200, path
    assert client.get("/static/../app/main.py").status_code == 404


def test_sound_references_become_audio_players() -> None:
    assert render_sounds("hola [sound:hola.mp3]") == (
        'hola <audio controls preload="none" src="hola.mp3"></audio>'
    )

"""Storing and finding media files (card images and audio).

Files live in one folder (settings.media_dir) under the names that cards use, e.g. the note text
<img src="paste-4c3d.jpg"> refers to the file "paste-4c3d.jpg". The phone loads them from the API,
so cards only ever contain file names, never folder paths.
"""

from pathlib import Path

from app.core.config import settings
from app.services.errors import InvalidInputError, NotFoundError

# Characters Windows does not allow in file names, plus path separators
_FORBIDDEN = set('<>:"/\\|?*')


def check_name(name: str) -> str:
    """Return the name if it is a plain file name; reject anything that could point elsewhere."""
    if (
        not name
        or name in (".", "..")
        or name.startswith(".")
        or len(name) > 200
        or any(c in _FORBIDDEN or ord(c) < 32 for c in name)
    ):
        raise InvalidInputError(f"Invalid media file name: {name!r}")
    return name


def media_path(name: str) -> Path:
    """The path of an existing media file."""
    path = settings.media_dir / check_name(name)
    if not path.is_file():
        raise NotFoundError(f"Media file {name!r} not found")
    return path


def _numbered(name: str, number: int) -> str:
    """"image.png" → "image (2).png"."""
    stem, dot, suffix = name.rpartition(".")
    return f"{stem} ({number}).{suffix}" if dot else f"{name} ({number})"


def store(name: str, content: bytes) -> str:
    """Save a media file and return the name it was saved under.

    If a file with this name already exists with the same content, nothing is written. If it
    exists with different content (e.g. two decks both using "image.png"), the new file gets a
    numbered name instead, so existing cards keep their file; the caller must then update the
    new cards' references to the returned name.
    """
    check_name(name)
    folder = settings.media_dir
    folder.mkdir(parents=True, exist_ok=True)
    candidate, number = name, 1
    while True:
        path = folder / candidate
        if not path.exists():
            path.write_bytes(content)
            return candidate
        if path.stat().st_size == len(content) and path.read_bytes() == content:
            return candidate
        number += 1
        candidate = _numbered(name, number)

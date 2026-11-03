"""Automatic import of Anki files dropped into the inbox folder.

Drop an .apkg or .colpkg file into settings.inbox_dir and the backend imports it:
- on success the file moves to settings.imported_dir (anki-exports)
- on failure it moves to inbox/failed, next to a .error.txt file explaining why

A file is only picked up once it has not changed for a few seconds, so a file that is still being
copied or downloaded is not read half-finished. The backend checks the inbox in a background
thread (start_watcher); process_inbox() does one check and can also be called directly.
"""

import logging
import shutil
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.anki_import import import_anki

log = logging.getLogger("recall_engine.inbox")

EXTENSIONS = {".apkg", ".colpkg"}
SETTLE_SECONDS = 3  # a file must be unchanged this long before it is imported


@dataclass(frozen=True)
class InboxResult:
    file: str
    imported: bool
    message: str


def _free_path(folder: Path, name: str) -> Path:
    """A path in folder for name that does not overwrite an existing file."""
    folder.mkdir(parents=True, exist_ok=True)
    path, number = folder / name, 1
    while path.exists():
        number += 1
        path = folder / f"{Path(name).stem} ({number}){Path(name).suffix}"
    return path


def _ready_files(inbox: Path, now: float) -> list[Path]:
    if not inbox.is_dir():
        return []
    return sorted(
        path for path in inbox.iterdir()
        if path.is_file() and path.suffix.lower() in EXTENSIONS and now - path.stat().st_mtime >= SETTLE_SECONDS
    )


def process_inbox(open_session: Callable[[], AbstractContextManager[Session]]) -> list[InboxResult]:
    """Import every settled Anki file in the inbox; each file in its own transaction."""
    results = []
    for path in _ready_files(settings.inbox_dir, time.time()):
        try:
            with open_session() as session:
                report = import_anki(session, path)
                session.commit()
        except Exception as error:  # any failure: keep the file aside with the reason
            target = _free_path(settings.inbox_dir / "failed", path.name)
            shutil.move(path, target)
            target.with_name(target.name + ".error.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
            log.warning("Inbox: could not import %s: %s", path.name, error)
            results.append(InboxResult(path.name, imported=False, message=str(error)))
            continue
        shutil.move(path, _free_path(settings.imported_dir, path.name))
        message = (f"{report.cards_created} new cards, {report.cards_updated} updated, "
                   f"{report.topics_created} new topics, {report.media_imported} media files")
        log.info("Inbox: imported %s (%s)", path.name, message)
        results.append(InboxResult(path.name, imported=True, message=message))
    return results


def start_watcher(open_session: Callable[[], AbstractContextManager[Session]]) -> threading.Event | None:
    """Check the inbox every settings.inbox_poll_seconds in a background thread.

    Returns an Event; set it to stop the thread. Returns None if checking is turned off.
    """
    if settings.inbox_poll_seconds <= 0:
        return None
    settings.inbox_dir.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()

    def run() -> None:
        while not stop.wait(settings.inbox_poll_seconds):
            try:
                process_inbox(open_session)
            except Exception:  # never let one bad check stop the watcher
                log.exception("Inbox check failed")

    threading.Thread(target=run, name="inbox-watcher", daemon=True).start()
    log.info("Inbox: watching %s", settings.inbox_dir)
    return stop

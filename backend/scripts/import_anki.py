"""Import an Anki collection (.colpkg) or deck package (.apkg) into the database.

Usage (from the backend folder, with the virtual environment active):
    python scripts/import_anki.py C:\\path\\to\\collection.colpkg --dry-run      # report only, saves nothing
    python scripts/import_anki.py C:\\path\\to\\collection.colpkg                # import
    python scripts/import_anki.py C:\\path\\to\\collection.colpkg --media-only   # only the images and audio

Back up the database first (scripts/backup-database.ps1 -Force). Importing the same file again
updates the earlier import instead of duplicating it, and brings back decks deleted since; use
--media-only to add media to a collection imported before without touching its cards.
"""

import argparse
import sys
import time
from dataclasses import asdict
from pathlib import Path

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.services.anki_import import AnkiFormatError, ImportReport, import_anki, import_anki_media


def run_import(path: Path, dry_run: bool) -> ImportReport:
    session = SessionLocal()
    try:
        # Media files cannot be rolled back, so a dry run leaves them out
        report = import_anki(session, path, with_media=not dry_run)
        if dry_run:
            session.rollback()
        else:
            session.commit()
        return report
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="the .colpkg or .apkg file exported from Anki")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="run the import, report, then undo it (no media)")
    mode.add_argument("--media-only", action="store_true", help="only copy the images and audio")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    started = time.perf_counter()
    try:
        report = import_anki_media(args.path) if args.media_only else run_import(args.path, args.dry_run)
    except AnkiFormatError as error:
        sys.exit(f"Cannot import: {error}")

    action = "Dry run (nothing saved)" if args.dry_run else "Media imported" if args.media_only else "Imported"
    target = settings.media_dir if args.media_only else f"database '{engine.url.database}'"
    print(f"{action}: {args.path.name} → {target} in {time.perf_counter() - started:.1f} s")
    for name, value in asdict(report).items():
        if name != "warnings":
            print(f"  {name.replace('_', ' '):24} {value}")
    for warning in report.warnings:
        print(f"  warning: {warning}")


if __name__ == "__main__":
    main()

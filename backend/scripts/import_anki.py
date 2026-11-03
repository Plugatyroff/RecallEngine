"""Import an Anki collection (.colpkg) or deck package (.apkg) into the database.

Usage (from the backend folder, with the virtual environment active):
    python scripts/import_anki.py C:\\path\\to\\collection.colpkg --dry-run   # report only, saves nothing
    python scripts/import_anki.py C:\\path\\to\\collection.colpkg             # import

Back up the database first (scripts/backup-database.ps1 -Force). Importing the same file again
updates the earlier import instead of duplicating it.
"""

import argparse
import sys
import time
from dataclasses import asdict
from pathlib import Path

from app.core.database import SessionLocal, engine
from app.services.anki_import import AnkiFormatError, import_anki


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="the .colpkg or .apkg file exported from Anki")
    parser.add_argument("--dry-run", action="store_true", help="run the import, report, then undo it")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    started = time.perf_counter()
    session = SessionLocal()
    try:
        report = import_anki(session, args.path)
        if args.dry_run:
            session.rollback()
        else:
            session.commit()
    except AnkiFormatError as error:
        session.rollback()
        sys.exit(f"Cannot import: {error}")
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()

    action = "Dry run (nothing saved)" if args.dry_run else "Imported"
    print(f"{action}: {args.path.name} → database '{engine.url.database}' in {time.perf_counter() - started:.1f} s")
    for name, value in asdict(report).items():
        if name != "warnings":
            print(f"  {name.replace('_', ' '):24} {value}")
    for warning in report.warnings:
        print(f"  warning: {warning}")


if __name__ == "__main__":
    main()

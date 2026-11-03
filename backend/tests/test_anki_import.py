"""Tests for importing Anki exports, using small collections built in each test."""

import json
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Card, Note, NoteType, Review, Tag, Topic
from app.services.anki_import import AnkiFormatError, import_anki

DAY_MS = 86_400_000
T0 = 1_700_000_000_000  # Anki IDs are creation times in milliseconds


def model(model_id: int, name: str, fields: list[str], templates: list[tuple[str, str, str]]) -> dict:
    return {
        "id": model_id, "name": name, "type": 0,
        "flds": [{"name": f, "ord": i} for i, f in enumerate(fields)],
        "tmpls": [{"name": n, "ord": i, "qfmt": q, "afmt": a} for i, (n, q, a) in enumerate(templates)],
    }


MODELS = {
    "1001": model(1001, "Basic", ["Front", "Back"], [("Card 1", "{{Front}}", "{{FrontSide}}<hr id=answer>{{Back}}")]),
    "1002": model(1002, "Basic (and reversed card)", ["Front", "Back"], [
        ("Card 1", "{{Front}}", "{{FrontSide}}<hr id=answer>{{Back}}"),
        ("Card 2", "{{Back}}", "{{FrontSide}}<hr id=answer>{{Front}}"),
    ]),
    "1003": model(1003, "Optional reverse", ["Word", "Meaning", "Add Reverse"], [
        ("Card 1", "{{Word}}", "{{Meaning}}"),
        ("Card 2", "{{#Add Reverse}}{{Meaning}}{{/Add Reverse}}", "{{Word}}"),
    ]),
    "1004": model(1004, "Unused", ["Text"], [("Card 1", "{{Text}}", "{{Text}}")]),  # no notes use it
}
DECKS = {
    "1": {"id": 1, "name": "Default"},
    "10": {"id": 10, "name": "Hungarian::Vocabulary"},
    "11": {"id": 11, "name": "Hungarian"},
    "12": {"id": 12, "name": "Mathematics"},
}
# (id, guid, model id, tags, fields)
NOTES = [
    (T0 + 1, "guid-maths", 1001, "exam", ["2+2", "<b>4</b>"]),
    (T0 + 2, "guid-alma", 1002, "A1 food", ["alma", "apple"]),
    (T0 + 3, "guid-szia", 1003, "a1", ["szia", "hi", ""]),
]
# (id, note id, deck id, ord)
CARDS = [
    (T0 + 11, T0 + 1, 12, 0),
    (T0 + 12, T0 + 2, 10, 0),
    (T0 + 13, T0 + 2, 10, 1),
    (T0 + 14, T0 + 3, 10, 0),  # no card for ord 1: "Add Reverse" is empty
]
# (id = review time in ms, card id, ease, ivl, time ms, type)
REVLOG = [
    (T0 + 1 * DAY_MS, T0 + 12, 3, 3, 4200, 0),   # Good, next in 3 days
    (T0 + 4 * DAY_MS, T0 + 12, 1, -600, 9000, 1),  # Again, next in 10 minutes
    (T0 + 5 * DAY_MS, T0 + 12, 0, 7, 0, 4),      # manual reschedule: not a review
]


def build_export(folder: Path, notes=NOTES, member: str = "collection.anki21") -> Path:
    database = folder / "collection.db"
    database.unlink(missing_ok=True)
    anki = sqlite3.connect(database)
    anki.executescript("""
        CREATE TABLE col (models TEXT, decks TEXT);
        CREATE TABLE notes (id INTEGER, guid TEXT, mid INTEGER, mod INTEGER, tags TEXT, flds TEXT);
        CREATE TABLE cards (id INTEGER, nid INTEGER, did INTEGER, odid INTEGER, ord INTEGER, mod INTEGER);
        CREATE TABLE revlog (id INTEGER, cid INTEGER, ease INTEGER, ivl INTEGER, time INTEGER, type INTEGER);
    """)
    anki.execute("INSERT INTO col VALUES (?, ?)", (json.dumps(MODELS), json.dumps(DECKS)))
    anki.executemany("INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?)",
                     [(i, g, m, i // 1000, f" {t} ", "\x1f".join(f)) for i, g, m, t, f in notes])
    anki.executemany("INSERT INTO cards VALUES (?, ?, ?, 0, ?, ?)", [(i, n, d, o, i // 1000) for i, n, d, o in CARDS])
    anki.executemany("INSERT INTO revlog VALUES (?, ?, ?, ?, ?, ?)", REVLOG)
    anki.commit()
    anki.close()
    export = folder / "export.colpkg"
    with zipfile.ZipFile(export, "w") as archive:
        archive.write(database, member)
    return export


def count(session: Session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_import_creates_topics_note_types_notes_cards_and_tags(session: Session, tmp_path: Path) -> None:
    report = import_anki(session, build_export(tmp_path))

    assert (report.note_types_created, report.notes_created, report.cards_created) == (3, 3, 4)  # not "Unused"
    vocab = session.scalar(select(Topic).where(Topic.name == "Vocabulary"))
    assert vocab.parent.name == "Hungarian"
    assert session.scalar(select(Topic).where(Topic.name == "Mathematics")) is not None
    assert session.scalar(select(Topic).where(Topic.name == "Default")) is None  # deck without cards

    alma = session.scalar(select(Note).where(Note.anki_guid == "guid-alma"))
    assert json.loads(alma.fields) == ["alma", "apple"]
    assert sorted(c.template_ord for c in alma.cards) == [0, 1]
    assert {c.topic.name for c in alma.cards} == {"Vocabulary"}
    maths = session.scalar(select(Note).where(Note.anki_guid == "guid-maths"))
    assert json.loads(maths.fields) == ["2+2", "<b>4</b>"]  # HTML kept as it is


def test_a_note_type_named_like_an_existing_one_gets_a_new_name(session: Session, tmp_path: Path) -> None:
    import_anki(session, build_export(tmp_path))

    imported = session.scalar(select(NoteType).where(NoteType.anki_id == 1001))
    assert imported.name == "Basic (Anki)"
    assert json.loads(imported.fields) == ["Front", "Back"]
    assert imported.templates[0].front_template == "{{Front}}"


def test_tags_are_shared_and_case_insensitive(session: Session, tmp_path: Path) -> None:
    import_anki(session, build_export(tmp_path))

    a1 = session.scalar(select(Tag).where(Tag.name == "A1"))
    assert sorted(n.anki_guid for n in a1.notes) == ["guid-alma", "guid-szia"]


def test_review_history_is_imported_and_replayed(session: Session, tmp_path: Path) -> None:
    report = import_anki(session, build_export(tmp_path))

    assert (report.reviews_imported, report.reviews_skipped) == (2, 1)
    card = session.scalar(select(Card).where(Card.anki_id == T0 + 12))
    reviews = sorted(card.reviews, key=lambda r: r.reviewed_at)
    assert [(r.grade, r.duration_ms, r.scheduler) for r in reviews] == [(3, 4200, "anki-import"), (1, 9000, "anki-import")]
    assert reviews[0].reviewed_at == datetime.fromtimestamp((T0 + DAY_MS) / 1000, UTC)

    state = card.review_state
    assert (state.review_count, state.lapse_count, state.status) == (2, 1, "relearning")
    assert state.last_reviewed_at == reviews[-1].reviewed_at
    assert "stability" in json.loads(state.scheduler_state)


def test_cards_without_history_stay_new(session: Session, tmp_path: Path) -> None:
    import_anki(session, build_export(tmp_path))

    card = session.scalar(select(Card).where(Card.anki_id == T0 + 11))
    assert card.review_state.status == "new"
    assert card.review_state.due_at is None


def test_importing_again_updates_instead_of_duplicating(session: Session, tmp_path: Path) -> None:
    import_anki(session, build_export(tmp_path))
    before = [count(session, m) for m in (NoteType, Topic, Note, Card, Review, Tag)]
    edited = [NOTES[0], (T0 + 2, "guid-alma", 1002, "A1 food", ["alma", "apple (fruit)"]), NOTES[2]]

    report = import_anki(session, build_export(tmp_path, notes=edited))

    assert [count(session, m) for m in (NoteType, Topic, Note, Card, Review, Tag)] == before
    assert (report.notes_created, report.notes_updated, report.cards_updated) == (0, 3, 4)
    assert report.reviews_already_present == 2
    alma = session.scalar(select(Note).where(Note.anki_guid == "guid-alma"))
    assert json.loads(alma.fields) == ["alma", "apple (fruit)"]


def test_newer_compressed_format_is_rejected_with_advice(session: Session, tmp_path: Path) -> None:
    export = build_export(tmp_path, member="collection.anki21b")

    with pytest.raises(AnkiFormatError, match="Support older Anki versions"):
        import_anki(session, export)


def test_a_file_that_is_not_an_export_is_rejected(session: Session, tmp_path: Path) -> None:
    not_an_export = tmp_path / "notes.colpkg"
    not_an_export.write_text("hello")

    with pytest.raises(AnkiFormatError):
        import_anki(session, not_an_export)

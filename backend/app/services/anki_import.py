"""Import Anki collections (.colpkg) and deck packages (.apkg).

What is imported:
- decks → topics (Anki's "Maths::Algebra" becomes the topic Maths → Algebra)
- note types with their fields and card templates
- notes (field values stay HTML; media references are kept, media files are not imported yet)
- cards, each in the topic of its deck
- tags
- the review history; each card's scheduling state is then rebuilt by replaying that history
  through the card's scheduler (FSRS by default)

Importing the same collection again updates what was imported before instead of duplicating it:
notes are matched by Anki's note GUID, cards and note types by their Anki IDs, reviews by card
and time. Everything happens in the caller's transaction, so an import either completes or
changes nothing.

Cloze note types are supported: their cards are numbered by gap and rendered by
app.services.templates. Image Occlusion cards import, but need media support to be usable.

Supported format: collections exported with "Support older Anki versions" (collection.anki21 or
collection.anki2 inside the file). Newer exports store a compressed collection.anki21b instead.
"""

import json
import sqlite3
import tempfile
import zipfile
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Card, Note, NoteType, NoteTypeTemplate, Review, ReviewState, Tag, Topic
from app.services.errors import InvalidInputError
from app.services.reviews import store_memory
from app.services.scheduling import DEFAULT_SCHEDULER, get_scheduler, replay

IMPORT_SCHEDULER_NAME = "anki-import"  # stored on imported reviews: who decided next_due_at
FIELD_SEPARATOR = "\x1f"  # Anki stores a note's fields in one text column, separated by this


class AnkiFormatError(InvalidInputError):
    """The file is not an Anki export this importer can read."""


@dataclass
class ImportReport:
    note_types_created: int = 0
    note_types_updated: int = 0
    topics_created: int = 0
    tags_created: int = 0
    notes_created: int = 0
    notes_updated: int = 0
    cards_created: int = 0
    cards_updated: int = 0
    reviews_imported: int = 0
    reviews_already_present: int = 0
    reviews_skipped: int = 0  # Anki entries that are not real reviews (e.g. manual reschedules)
    warnings: list[str] = field(default_factory=list)


@contextmanager
def open_collection(path: Path) -> Iterator[sqlite3.Connection]:
    """Open the SQLite database inside an Anki export, read-only."""
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError) as error:
        raise AnkiFormatError(f"{path} is not an Anki export file: {error}") from error
    with archive, tempfile.TemporaryDirectory() as folder:
        names = set(archive.namelist())
        member = next((n for n in ("collection.anki21", "collection.anki2") if n in names), None)
        if "collection.anki21b" in names and member != "collection.anki21":
            raise AnkiFormatError(
                "This export uses Anki's newer compressed format. Export again in Anki with "
                "'Support older Anki versions' ticked."
            )
        if member is None:
            raise AnkiFormatError(f"{path} contains no Anki collection")
        database = Path(archive.extract(member, folder))
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            yield connection
        finally:
            connection.close()


def _from_ms(milliseconds: int) -> datetime:
    return datetime.fromtimestamp(milliseconds / 1000, UTC)


def import_anki(session: Session, path: Path) -> ImportReport:
    report = ImportReport()
    with open_collection(path) as anki:
        models_json, decks_json = anki.execute("SELECT models, decks FROM col").fetchone()
        decks: dict[str, dict] = json.loads(decks_json)
        # Anki also exports note types that no note uses; only import the ones in use
        used = {row[0] for row in anki.execute("SELECT DISTINCT mid FROM notes")}
        models = {key: m for key, m in json.loads(models_json).items() if int(m["id"]) in used}

        note_types = _import_note_types(session, models, report)
        topics = _import_topics(session, decks, anki, report)
        notes = _import_notes(session, anki, note_types, models, report)
        cards = _import_cards(session, anki, notes, topics, report)
        _import_reviews(session, anki, cards, report)

    _rebuild_schedules(cards.values())
    session.flush()
    return report


def _import_note_types(session: Session, models: dict[str, dict], report: ImportReport) -> dict[int, NoteType]:
    existing = {t.anki_id: t for t in session.scalars(
        select(NoteType).where(NoteType.anki_id.is_not(None)).options(selectinload(NoteType.templates))
    )}
    taken_names = set(session.scalars(select(NoteType.name)))
    result: dict[int, NoteType] = {}
    for model in models.values():
        anki_id = int(model["id"])
        fields = [f["name"] for f in sorted(model["flds"], key=lambda f: f["ord"])]
        note_type = existing.get(anki_id)
        if note_type is None:
            name, number = model["name"], 1
            while name in taken_names:  # e.g. Anki's "Basic" next to Recall Engine's own "Basic"
                number += 1
                name = f"{model['name']} (Anki{'' if number == 2 else f' {number - 1}'})"
            taken_names.add(name)
            note_type = NoteType(name=name, anki_id=anki_id)
            session.add(note_type)
            report.note_types_created += 1
        else:
            report.note_types_updated += 1
        note_type.fields = json.dumps(fields, ensure_ascii=False)
        templates = {t.ord: t for t in note_type.templates}
        for tmpl in model["tmpls"]:
            template = templates.get(tmpl["ord"])
            if template is None:
                template = NoteTypeTemplate(ord=tmpl["ord"])
                note_type.templates.append(template)
            template.name = tmpl["name"]
            template.front_template = tmpl["qfmt"]
            template.back_template = tmpl["afmt"]
        result[anki_id] = note_type
    return result


def _import_topics(session: Session, decks: dict[str, dict], anki: sqlite3.Connection,
                   report: ImportReport) -> dict[int, Topic]:
    """Create a topic for every deck that has cards (and for its parents). Returns deck id → topic."""
    by_path: dict[tuple[str, ...], Topic] = {}
    all_topics = list(session.scalars(select(Topic)))
    by_id = {t.id: t for t in all_topics}

    def path_of(topic: Topic) -> tuple[str, ...]:
        names = []
        while topic is not None:
            names.append(topic.name)
            topic = by_id.get(topic.parent_id)
        return tuple(reversed(names))

    for topic in all_topics:
        by_path[path_of(topic)] = topic

    def topic_for(path: tuple[str, ...]) -> Topic:
        if path not in by_path:
            parent = topic_for(path[:-1]) if len(path) > 1 else None
            topic = Topic(name=path[-1], parent=parent)
            session.add(topic)
            by_path[path] = topic
            report.topics_created += 1
        return by_path[path]

    used = {row[0] for row in anki.execute("SELECT DISTINCT CASE WHEN odid != 0 THEN odid ELSE did END FROM cards")}
    result = {}
    for deck_id in used:
        deck = decks.get(str(deck_id))
        name = deck["name"] if deck else "Anki import"
        path = tuple(part.strip()[:200] or "(unnamed)" for part in name.split("::"))
        result[deck_id] = topic_for(path)
    return result


def _import_notes(session: Session, anki: sqlite3.Connection, note_types: dict[int, NoteType],
                  models: dict[str, dict], report: ImportReport) -> dict[int, Note]:
    existing = {n.anki_guid: n for n in session.scalars(
        select(Note).where(Note.anki_guid.is_not(None)).options(selectinload(Note.tags))
    )}
    # Keyed case-insensitively, like Anki tags and the database's text comparison
    tags = {t.name.casefold(): t for t in session.scalars(select(Tag))}

    def tag(name: str) -> Tag:
        key = name[:200].casefold()
        if key not in tags:
            tags[key] = Tag(name=name[:200])
            report.tags_created += 1
        return tags[key]

    result: dict[int, Note] = {}
    for note_id, guid, model_id, modified, tag_text, fields_text in anki.execute(
        "SELECT id, guid, mid, mod, tags, flds FROM notes"
    ):
        field_count = len(models[str(model_id)]["flds"])
        values = (fields_text.split(FIELD_SEPARATOR) + [""] * field_count)[:field_count]
        note = existing.get(guid)
        if note is None:
            note = Note(anki_guid=guid, created_at=_from_ms(note_id))
            session.add(note)
            report.notes_created += 1
        else:
            report.notes_updated += 1
        note.note_type = note_types[model_id]
        note.fields = json.dumps(values, ensure_ascii=False)
        note.tags = list({id(t): t for t in (tag(name) for name in tag_text.split())}.values())
        note.updated_at = datetime.fromtimestamp(modified, UTC)
        result[note_id] = note
    return result


def _import_cards(session: Session, anki: sqlite3.Connection, notes: dict[int, Note],
                  topics: dict[int, Topic], report: ImportReport) -> dict[int, Card]:
    existing = {c.anki_id: c for c in session.scalars(
        select(Card).where(Card.anki_id.is_not(None)).options(selectinload(Card.review_state), selectinload(Card.reviews))
    )}
    result: dict[int, Card] = {}
    for card_id, note_id, deck_id, original_deck_id, ord_, modified in anki.execute(
        "SELECT id, nid, did, odid, ord, mod FROM cards"
    ):
        card = existing.get(card_id)
        if card is None:
            card = Card(anki_id=card_id, created_at=_from_ms(card_id))
            card.review_state = ReviewState(scheduler=DEFAULT_SCHEDULER)
            session.add(card)
            report.cards_created += 1
        else:
            report.cards_updated += 1
        card.note = notes[note_id]
        card.template_ord = ord_
        card.topic = topics[original_deck_id or deck_id]  # cards in a filtered deck belong to their original deck
        card.updated_at = datetime.fromtimestamp(modified, UTC)
        result[card_id] = card
    return result


def _import_reviews(session: Session, anki: sqlite3.Connection, cards: dict[int, Card], report: ImportReport) -> None:
    present = defaultdict(set)
    for card in cards.values():
        for review in card.reviews:
            present[card.anki_id].add(review.reviewed_at)

    for review_id, card_id, ease, interval, duration_ms, kind in anki.execute(
        "SELECT id, cid, ease, ivl, time, type FROM revlog ORDER BY id"
    ):
        card = cards.get(card_id)
        # ease 0 / type 4 are manual reschedules, not answers; reviews of deleted cards are dropped
        if card is None or ease not in (1, 2, 3, 4) or kind == 4:
            report.reviews_skipped += 1
            continue
        reviewed_at = _from_ms(review_id)
        if reviewed_at in present[card_id]:
            report.reviews_already_present += 1
            continue
        # Anki stores the resulting interval as negative seconds (learning) or positive days
        next_due = reviewed_at + (timedelta(seconds=-interval) if interval < 0 else timedelta(days=interval))
        card.reviews.append(Review(reviewed_at=reviewed_at, grade=ease, duration_ms=duration_ms,
                                   next_due_at=next_due, scheduler=IMPORT_SCHEDULER_NAME))
        present[card_id].add(reviewed_at)
        report.reviews_imported += 1


def _rebuild_schedules(cards) -> None:
    """Replay each card's full review history through its scheduler to set its current state."""
    for card in cards:
        history = sorted(card.reviews, key=lambda review: review.reviewed_at)
        scheduler = get_scheduler(card.review_state.scheduler)
        store_memory(card.review_state, replay(scheduler, [(r.grade, r.reviewed_at) for r in history]))

"""Fill the database with fake topics, notes, cards and review history for development.

Usage (from the backend folder, with the virtual environment active):
    python scripts/seed.py            # only runs if the database is empty
    python scripts/seed.py --reset    # deletes ALL existing data first

Never use --reset once the database holds real cards you want to keep.
"""

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models import (
    Card,
    Note,
    NoteType,
    NoteTypeTemplate,
    Review,
    ReviewState,
    Tag,
    Topic,
    note_tags,
)

NOW = datetime.now(UTC)
HOUR = timedelta(hours=1)
MINUTE = timedelta(minutes=1)
DAY = timedelta(days=1)

BACK_TEMPLATE = "{{FrontSide}}\n\n<hr id=answer>\n\n{{%s}}"

# name -> (fields, [(template name, front template, back template)])
NOTE_TYPES = {
    "Basic": (["Front", "Back"], [("Card 1", "{{Front}}", BACK_TEMPLATE % "Back")]),
    "Basic (and reversed card)": (
        ["Front", "Back"],
        [("Card 1", "{{Front}}", BACK_TEMPLATE % "Back"), ("Card 2", "{{Back}}", BACK_TEMPLATE % "Front")],
    ),
}

# topic path -> (note type, kind, tags, [(front, back)]). Fields hold HTML; math uses \( ... \).
NOTES: dict[tuple[str, ...], tuple[str, str, list[str], list[tuple[str, str]]]] = {
    ("Mathematics", "Linear Algebra", "Matrices", "Determinants"): ("Basic", "theorem", ["exam"], [
        (r"Determinant of \(\begin{pmatrix} a & b \\ c & d \end{pmatrix}\)?", r"\(ad - bc\)"),
        ("State the product rule for determinants.", r"\(\det(AB) = \det(A)\det(B)\)"),
        ("When is a square matrix invertible?", r"Exactly when \(\det(A) \neq 0\)."),
    ]),
    ("Mathematics", "Linear Algebra", "Matrices", "Matrix Operations"): ("Basic", "definition", [], [
        (r"When can \(A\) and \(B\) be multiplied as \(AB\)?",
         r"When the number of columns of \(A\) equals the number of rows of \(B\)."),
        ("Is matrix multiplication commutative?", r"<b>No</b>: in general \(AB \neq BA\)."),
    ]),
    ("Mathematics", "Calculus", "Derivatives"): ("Basic", "definition", [], [
        (r"Define the derivative of \(f\) at \(x\).",
         r"\(f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}\)"),
        (r"Differentiate \(x^n\).", r"\(n x^{n-1}\)"),
    ]),
    ("Hungarian", "Vocabulary"): ("Basic (and reversed card)", "vocab", ["A1"], [
        ("alma", "apple"),
        ("kutya", "dog"),
        ("ház", "house"),
        ("könyv", "book"),
        ("víz", "water"),
        ("szőlő", "grapes"),
    ]),
    ("Hungarian", "Grammar"): ("Basic", "basic", ["A1"], [
        ("What does the suffix <i>-ban/-ben</i> express?",
         "Being inside something: <i>a házban</i> = in the house."),
    ]),
    ("Electronics", "Microcontrollers"): ("Basic", "definition", [], [
        ("What does GPIO stand for?", "General-Purpose Input/Output"),
        ("What is a pull-up resistor for?",
         "It holds an input pin at a defined high level when nothing drives it."),
    ]),
    ("Electronics", "Digital Electronics"): ("Basic", "basic", [], [
        ("What is the output of a NAND gate when both inputs are 1?", "0"),
    ]),
}

# Example schedules, applied to cards in turn, so the data shows every state:
# (status, due_at, review history as (time ago, grade))
EXAMPLE_STATES = [
    ("new", None, []),
    ("learning", NOW + 1 * HOUR, [(1 * HOUR, 3)]),
    ("learning", NOW - 30 * MINUTE, [(8 * HOUR, 3), (6 * HOUR + 30 * MINUTE, 3)]),
    ("relearning", NOW - 10 * MINUTE, [(3 * DAY, 3), (2 * HOUR, 1)]),
    ("review", NOW + 2 * DAY, [(3 * DAY, 3), (3 * DAY - 2 * HOUR, 3), (2 * DAY, 4), (1 * DAY, 3)]),
]


def reset(session: Session) -> None:
    session.execute(delete(Review))
    session.execute(delete(ReviewState))
    session.execute(delete(Card))
    session.execute(delete(note_tags))
    session.execute(delete(Note))
    session.execute(delete(Tag))
    session.execute(delete(NoteTypeTemplate))
    session.execute(delete(NoteType))
    # Topics reference each other, so detach them from their parents before deleting.
    session.execute(update(Topic).values(parent_id=None))
    session.execute(delete(Topic))


def get_topic(session: Session, path: tuple[str, ...], cache: dict) -> Topic:
    """Return the topic at this path, creating it and any missing parents."""
    if path in cache:
        return cache[path]
    parent = get_topic(session, path[:-1], cache) if len(path) > 1 else None
    topic = Topic(name=path[-1], parent=parent)
    session.add(topic)
    cache[path] = topic
    return topic


def get_note_type(session: Session, name: str) -> NoteType:
    """Return the note type with this name, creating it if needed (the migration creates "Basic")."""
    note_type = session.scalar(select(NoteType).where(NoteType.name == name))
    if note_type is None:
        fields, templates = NOTE_TYPES[name]
        note_type = NoteType(name=name, fields=json.dumps(fields))
        for ord_, (template_name, front, back) in enumerate(templates):
            note_type.templates.append(
                NoteTypeTemplate(ord=ord_, name=template_name, front_template=front, back_template=back)
            )
        session.add(note_type)
    return note_type


def get_tag(session: Session, name: str, cache: dict) -> Tag:
    if name not in cache:
        cache[name] = Tag(name=name)
    return cache[name]


def add_schedule(card: Card, example: int) -> None:
    status, due_at, history = EXAMPLE_STATES[example % len(EXAMPLE_STATES)]
    card.review_state = ReviewState(
        status=status,
        due_at=due_at,
        last_reviewed_at=NOW - history[-1][0] if history else None,
        review_count=len(history),
        lapse_count=sum(1 for _, grade in history if grade == 1),
    )
    for i, (ago, grade) in enumerate(history):
        next_due = NOW - history[i + 1][0] if i + 1 < len(history) else due_at
        card.reviews.append(Review(reviewed_at=NOW - ago, grade=grade, duration_ms=4000 + 1500 * i,
                                   next_due_at=next_due, scheduler="seed"))


def seed(session: Session) -> tuple[int, int]:
    topics: dict[tuple[str, ...], Topic] = {}
    tags: dict[str, Tag] = {}
    note_count = card_count = 0
    for path, (type_name, kind, tag_names, contents) in NOTES.items():
        topic = get_topic(session, path, topics)
        note_type = get_note_type(session, type_name)
        for front, back in contents:
            note = Note(note_type=note_type, fields=json.dumps([front, back], ensure_ascii=False),
                        kind=kind, tags=[get_tag(session, t, tags) for t in tag_names],
                        created_at=NOW - 4 * DAY, updated_at=NOW - 4 * DAY)
            for template in note_type.templates:
                card = Card(template_ord=template.ord, topic=topic,
                            created_at=NOW - 4 * DAY, updated_at=NOW - 4 * DAY)
                add_schedule(card, card_count)
                note.cards.append(card)
                card_count += 1
            session.add(note)
            note_count += 1
    return note_count, card_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete all existing data first")
    args = parser.parse_args()

    with SessionLocal.begin() as session:
        existing = session.scalar(select(func.count()).select_from(Topic))
        if existing and not args.reset:
            sys.exit(f"Database '{engine.url.database}' already has {existing} topics. "
                     "Use --reset to delete everything and re-seed.")
        if args.reset:
            reset(session)
        notes, cards = seed(session)

    print(f"Seeded {notes} notes ({cards} cards) into '{engine.url.database}'.")


if __name__ == "__main__":
    main()

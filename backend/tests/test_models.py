"""Tests for the database tables and the rules the database itself enforces."""

import itertools
import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Card, Note, NoteType, NoteTypeTemplate, Review, ReviewState, Tag, Topic


_note_type_numbers = itertools.count(1)


def make_note_type(name: str | None = None, templates: int = 1) -> NoteType:
    # Unique names, because the migrations already create a note type called "Basic"
    name = name or f"Test type {next(_note_type_numbers)}"
    note_type = NoteType(name=name, fields=json.dumps(["Front", "Back"]))
    for ord_ in range(templates):
        note_type.templates.append(
            NoteTypeTemplate(ord=ord_, name=f"Card {ord_ + 1}", front_template="{{Front}}",
                             back_template="{{Back}}")
        )
    return note_type


def make_note(note_type: NoteType, topic: Topic, front: str = "Q", back: str = "A", **fields) -> Note:
    """A note with one card (plus its review state) per template of its note type."""
    note = Note(note_type=note_type, fields=json.dumps([front, back]), **fields)
    for template in note_type.templates:
        card = Card(template_ord=template.ord, topic=topic)
        card.review_state = ReviewState()
        note.cards.append(card)
    return note


def make_card(topic: Topic | None = None) -> Card:
    return make_note(make_note_type(), topic or Topic(name="Hungarian")).cards[0]


# --- topics ---------------------------------------------------------------------------------

def test_topics_form_a_tree(session: Session) -> None:
    maths = Topic(name="Mathematics")
    algebra = Topic(name="Linear Algebra", parent=maths)
    Topic(name="Matrices", parent=algebra)
    session.add(maths)
    session.flush()

    top_level = session.scalars(select(Topic).where(Topic.parent_id.is_(None))).all()
    assert [t.name for t in top_level] == ["Mathematics"]
    assert [t.name for t in maths.children] == ["Linear Algebra"]
    assert algebra.children[0].parent_id == algebra.id


def test_sibling_topics_need_unique_names(session: Session) -> None:
    maths = Topic(name="Mathematics")
    session.add_all([Topic(name="Basics", parent=maths), Topic(name="Basics", parent=maths)])

    with pytest.raises(IntegrityError):
        session.flush()


def test_same_name_is_allowed_under_different_parents(session: Session) -> None:
    session.add_all(
        [
            Topic(name="Basics", parent=Topic(name="Mathematics")),
            Topic(name="Basics", parent=Topic(name="Hungarian")),
        ]
    )
    session.flush()


def test_topic_with_subtopics_cannot_be_deleted(session: Session) -> None:
    maths = Topic(name="Mathematics")
    Topic(name="Calculus", parent=maths)
    session.add(maths)
    session.flush()

    with pytest.raises(IntegrityError):
        session.execute(delete(Topic).where(Topic.id == maths.id))


def test_topic_with_cards_cannot_be_deleted(session: Session) -> None:
    topic = Topic(name="Vocabulary")
    session.add(make_card(topic))
    session.flush()

    with pytest.raises(IntegrityError):
        session.execute(delete(Topic).where(Topic.id == topic.id))


# --- notes and cards ------------------------------------------------------------------------

def test_note_with_two_templates_has_two_cards_sharing_its_content(session: Session) -> None:
    note = make_note(make_note_type(templates=2), Topic(name="Hungarian"),
                     front="alma", back="apple")
    session.add(note)
    session.flush()

    assert [c.template_ord for c in note.cards] == [0, 1]
    assert all(c.note.fields == '["alma", "apple"]' for c in note.cards)


def test_a_template_produces_only_one_card_per_note(session: Session) -> None:
    card = make_card()
    card.note.cards.append(Card(template_ord=0, topic=card.topic))
    session.add(card)

    with pytest.raises(IntegrityError):
        session.flush()


def test_new_note_and_card_defaults(session: Session) -> None:
    card = make_card()
    session.add(card)
    session.flush()
    session.refresh(card)

    assert card.note.kind == "basic"
    assert card.note.priority == 2
    assert card.review_state.status == "new"
    assert card.review_state.due_at is None
    assert card.review_state.scheduler == "fsrs"
    assert card.created_at.tzinfo == UTC


@pytest.mark.parametrize(
    "fields", [{"priority": 4}, {"priority": 0}, {"kind": "poem"}]
)
def test_note_rejects_invalid_values(session: Session, fields: dict) -> None:
    session.add(make_note(make_note_type(), Topic(name="Hungarian"), **fields))

    with pytest.raises(IntegrityError):
        session.flush()


def test_note_fields_must_be_json(session: Session) -> None:
    note = make_note(make_note_type(), Topic(name="Hungarian"))
    note.fields = "alma, apple"
    session.add(note)

    with pytest.raises(IntegrityError):
        session.flush()


def test_note_type_in_use_cannot_be_deleted(session: Session) -> None:
    note = make_note(make_note_type(), Topic(name="Hungarian"))
    session.add(note)
    session.flush()

    with pytest.raises(IntegrityError):
        session.execute(delete(NoteType).where(NoteType.id == note.note_type_id))


def test_deleting_a_note_deletes_its_cards_and_review_data(session: Session) -> None:
    note = make_note(make_note_type(templates=2), Topic(name="Hungarian"))
    now = datetime.now(UTC)
    note.cards[0].reviews.append(Review(reviewed_at=now, grade=3, next_due_at=now, scheduler="test"))
    session.add(note)
    session.flush()
    card_ids = [c.id for c in note.cards]

    session.execute(delete(Note).where(Note.id == note.id))

    assert session.scalars(select(Card).where(Card.id.in_(card_ids))).all() == []
    assert session.scalars(select(ReviewState).where(ReviewState.card_id.in_(card_ids))).all() == []
    assert session.scalars(select(Review).where(Review.card_id.in_(card_ids))).all() == []


def test_anki_ids_are_unique_but_may_be_missing_on_many_notes(session: Session) -> None:
    note_type, topic = make_note_type(), Topic(name="Hungarian")
    # Several notes without an Anki ID are fine (a plain UNIQUE constraint would reject this)
    session.add_all([make_note(note_type, topic), make_note(note_type, topic)])
    session.flush()

    session.add_all([make_note(note_type, topic, anki_guid="abc"), make_note(note_type, topic, anki_guid="abc")])
    with pytest.raises(IntegrityError):
        session.flush()


def test_notes_can_share_tags(session: Session) -> None:
    note_type, topic, tag = make_note_type(), Topic(name="Spanish"), Tag(name="top-1000")
    first, second = make_note(note_type, topic), make_note(note_type, topic)
    first.tags.append(tag)
    second.tags.append(tag)
    session.add_all([first, second])
    session.flush()

    session.execute(delete(Note).where(Note.id == first.id))
    session.expire_all()

    assert [n.id for n in session.get(Tag, tag.id).notes] == [second.id]


# --- scheduling data ------------------------------------------------------------------------

def test_review_grade_must_be_between_1_and_4(session: Session) -> None:
    card = make_card()
    now = datetime.now(UTC)
    card.reviews.append(Review(reviewed_at=now, grade=5, next_due_at=now, scheduler="test"))
    session.add(card)

    with pytest.raises(IntegrityError):
        session.flush()


def test_scheduler_state_must_be_json(session: Session) -> None:
    card = make_card()
    card.review_state.scheduler_state = '{"stability": 2.3}'
    session.add(card)
    session.flush()

    card.review_state.scheduler_state = "stability=2.3"
    with pytest.raises(IntegrityError):
        session.flush()


def test_relearning_status_is_allowed(session: Session) -> None:
    card = make_card()
    card.review_state.status = "relearning"
    session.add(card)
    session.flush()


def test_timestamps_are_stored_in_utc(session: Session) -> None:
    budapest_winter = timezone(timedelta(hours=1))
    due = datetime(2026, 11, 3, 14, 0, tzinfo=budapest_winter)
    card = make_card()
    card.review_state.due_at = due
    session.add(card)
    session.flush()
    session.expire_all()

    loaded = session.get(ReviewState, card.id)
    assert loaded.due_at == due
    assert loaded.due_at.tzinfo == UTC
    assert loaded.due_at.hour == 13


def test_naive_datetimes_are_rejected(session: Session) -> None:
    card = make_card()
    card.review_state.due_at = datetime(2026, 11, 3, 14, 0)
    session.add(card)

    with pytest.raises(Exception, match="time-zone-aware"):
        session.flush()

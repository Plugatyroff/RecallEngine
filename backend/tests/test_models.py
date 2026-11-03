"""Tests for the database tables and the rules the database itself enforces."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Card, Review, ReviewState, Topic


def make_card(topic: Topic, **fields) -> Card:
    card = Card(topic=topic, front="Q", back="A", **fields)
    card.review_state = ReviewState()
    return card


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


def test_new_card_defaults(session: Session) -> None:
    card = make_card(Topic(name="Hungarian"))
    session.add(card)
    session.flush()
    session.refresh(card)

    assert card.kind == "basic"
    assert card.priority == 2
    assert card.review_state.status == "new"
    assert card.review_state.due_at is None
    assert card.created_at.tzinfo == UTC


@pytest.mark.parametrize("fields", [{"priority": 4}, {"priority": 0}, {"kind": "poem"}])
def test_card_rejects_invalid_values(session: Session, fields: dict) -> None:
    session.add(make_card(Topic(name="Hungarian"), **fields))

    with pytest.raises(IntegrityError):
        session.flush()


def test_review_grade_must_be_between_1_and_4(session: Session) -> None:
    card = make_card(Topic(name="Hungarian"))
    now = datetime.now(UTC)
    card.reviews.append(
        Review(reviewed_at=now, grade=5, next_due_at=now, scheduler_version="test")
    )
    session.add(card)

    with pytest.raises(IntegrityError):
        session.flush()


def test_deleting_a_card_deletes_its_review_data(session: Session) -> None:
    card = make_card(Topic(name="Hungarian"))
    now = datetime.now(UTC)
    card.reviews.append(Review(reviewed_at=now, grade=3, next_due_at=now, scheduler_version="test"))
    session.add(card)
    session.flush()

    session.execute(delete(Card).where(Card.id == card.id))

    assert session.scalars(select(ReviewState).where(ReviewState.card_id == card.id)).all() == []
    assert session.scalars(select(Review).where(Review.card_id == card.id)).all() == []


def test_timestamps_are_stored_in_utc(session: Session) -> None:
    budapest_winter = timezone(timedelta(hours=1))
    due = datetime(2026, 11, 3, 14, 0, tzinfo=budapest_winter)
    card = make_card(Topic(name="Hungarian"))
    card.review_state.due_at = due
    session.add(card)
    session.flush()
    session.expire_all()

    loaded = session.get(ReviewState, card.id)
    assert loaded.due_at == due
    assert loaded.due_at.tzinfo == UTC
    assert loaded.due_at.hour == 13


def test_naive_datetimes_are_rejected(session: Session) -> None:
    card = make_card(Topic(name="Hungarian"))
    card.review_state.due_at = datetime(2026, 11, 3, 14, 0)
    session.add(card)

    with pytest.raises(Exception, match="time-zone-aware"):
        session.flush()

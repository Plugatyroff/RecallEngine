"""Tests for recording reviews in the database."""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Card, NoteType, Review, Topic
from app.services.reviews import record_review
from app.services.scheduling import AGAIN, GOOD, get_scheduler
from tests.test_models import make_note

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


def new_card(session: Session, scheduler: str = "fsrs") -> Card:
    """A new card of the "Basic" note type that the migrations create."""
    basic = session.scalar(
        select(NoteType).where(NoteType.name == "Basic").options(selectinload(NoteType.templates))
    )
    card = make_note(basic, Topic(name="Hungarian")).cards[0]
    card.review_state.scheduler = scheduler
    session.add(card)
    session.flush()
    return card


def test_recording_a_review_reschedules_the_card_and_logs_it(session: Session) -> None:
    card = new_card(session)

    review = record_review(card, GOOD, NOW, duration_ms=3200)
    session.flush()
    session.expire_all()

    state = card.review_state
    assert state.status == "review"
    assert state.due_at > NOW
    assert state.last_reviewed_at == NOW
    assert state.review_count == 1
    assert "stability" in json.loads(state.scheduler_state)

    logged = session.get(Review, review.id)
    assert (logged.grade, logged.duration_ms, logged.scheduler) == (GOOD, 3200, "fsrs")
    assert logged.next_due_at == state.due_at


def test_each_card_is_scheduled_by_its_own_scheduler(session: Session) -> None:
    card = new_card(session, scheduler="hours")

    record_review(card, GOOD, NOW)
    first_due = card.review_state.due_at
    record_review(card, AGAIN, first_due)

    assert first_due - NOW == get_scheduler("hours").interval(0)
    assert [r.scheduler for r in card.reviews] == ["hours", "hours"]
    assert json.loads(card.review_state.scheduler_state) == {"step": -1}

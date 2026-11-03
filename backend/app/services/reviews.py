"""Connects the memory schedulers to the database tables."""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Card, Review, ReviewState
from app.services.errors import NotFoundError
from app.services.scheduling import GRADES, CardMemory, get_scheduler, replay


def memory_of(review_state: ReviewState) -> CardMemory:
    """Read a card's stored scheduling data into the form schedulers work with."""
    return CardMemory(
        status=review_state.status,
        due_at=review_state.due_at,
        last_reviewed_at=review_state.last_reviewed_at,
        review_count=review_state.review_count,
        lapse_count=review_state.lapse_count,
        state=json.loads(review_state.scheduler_state) if review_state.scheduler_state else {},
    )


def memory_for(card: Card) -> CardMemory:
    """The card's memory as its scheduler needs it.

    A card can have review history but no data from its scheduler, e.g. after a migration, an
    import, or a switch to another scheduler. Its memory is then rebuilt by replaying the history.
    """
    review_state = card.review_state
    if review_state.status == "new" or review_state.scheduler_state:
        return memory_of(review_state)
    history = sorted(card.reviews, key=lambda review: review.reviewed_at)
    return replay(get_scheduler(review_state.scheduler), [(r.grade, r.reviewed_at) for r in history])


def store_memory(review_state: ReviewState, memory: CardMemory) -> None:
    review_state.status = memory.status
    review_state.due_at = memory.due_at
    review_state.last_reviewed_at = memory.last_reviewed_at
    review_state.review_count = memory.review_count
    review_state.lapse_count = memory.lapse_count
    review_state.scheduler_state = json.dumps(memory.state) if memory.state else None


def record_review(card: Card, grade: int, reviewed_at: datetime, duration_ms: int | None = None) -> Review:
    """Reschedule a card after a review and add the review to its history.

    The card is rescheduled by the scheduler that owns it (review_states.scheduler).
    Changes are made to the ORM objects; the caller commits the session.
    """
    scheduler = get_scheduler(card.review_state.scheduler)
    memory = scheduler.review(memory_for(card), grade, reviewed_at)
    store_memory(card.review_state, memory)
    review = Review(
        reviewed_at=reviewed_at,
        grade=grade,
        duration_ms=duration_ms,
        next_due_at=memory.due_at,
        scheduler=scheduler.name,
    )
    card.reviews.append(review)
    return review


def submit_review(session: Session, card_id: int, grade: int, reviewed_at: datetime,
                  duration_ms: int | None = None) -> Card:
    card = session.get(Card, card_id)
    if card is None:
        raise NotFoundError(f"Card {card_id} not found")
    record_review(card, grade, reviewed_at, duration_ms)
    session.flush()
    return card


def next_due_by_grade(card: Card, now: datetime) -> dict[int, datetime]:
    """When the card would come back for each possible grade, e.g. to label the grade buttons."""
    scheduler = get_scheduler(card.review_state.scheduler)
    memory = memory_for(card)
    return {grade: scheduler.review(memory, grade, now).due_at for grade in GRADES}

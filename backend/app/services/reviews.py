"""Connects the memory schedulers to the database tables."""

import json
from datetime import datetime

from app.models import Card, Review, ReviewState
from app.services.scheduling import CardMemory, get_scheduler


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
    memory = scheduler.review(memory_of(card.review_state), grade, reviewed_at)
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

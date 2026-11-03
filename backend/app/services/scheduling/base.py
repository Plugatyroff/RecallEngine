"""The interface every memory scheduler implements, and the data it works with.

A memory scheduler answers one question: after this review, when should the card ideally be
seen again? It knows nothing about the database, notifications or sessions, so schedulers can
be swapped (FSRS, fixed steps, anything else) without touching the rest of the app.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, Protocol, runtime_checkable

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
GRADES = (AGAIN, HARD, GOOD, EASY)


@dataclass(frozen=True)
class CardMemory:
    """What a scheduler knows about one card.

    The first five fields mean the same for every scheduler and are what the rest of the app
    relies on. `state` holds the scheduler's own private data (e.g. FSRS stability) and must
    contain only JSON-compatible values, because it is stored as JSON.
    """

    status: str = "new"  # new, learning, review or relearning
    due_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    review_count: int = 0
    lapse_count: int = 0
    state: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MemoryScheduler(Protocol):
    """Any class with these members can be used as a scheduler."""

    # Stored with each card, so the card is always rescheduled by the scheduler that owns it
    name: str

    def review(self, memory: CardMemory, grade: int, reviewed_at: datetime) -> CardMemory:
        """Return the card's memory after a review with this grade at this (actual) time."""
        ...

    def recall_probability(self, memory: CardMemory, at: datetime) -> float | None:
        """Estimated chance (0-1) of remembering the card at `at`, or None if unknown."""
        ...


def check_review(grade: int, reviewed_at: datetime) -> None:
    if grade not in GRADES:
        raise ValueError(f"grade must be one of {GRADES}, got {grade!r}")
    if reviewed_at.tzinfo is None:
        raise ValueError("reviewed_at must be a time-zone-aware datetime")


def after_review(
    memory: CardMemory,
    grade: int,
    reviewed_at: datetime,
    *,
    status: str,
    interval: timedelta,
    state: dict[str, Any],
) -> CardMemory:
    """Build the memory after a review: the bookkeeping that is the same for every scheduler."""
    lapsed = grade == AGAIN and memory.status == "review"
    return replace(
        memory,
        status=status,
        due_at=reviewed_at + interval,
        last_reviewed_at=reviewed_at,
        review_count=memory.review_count + 1,
        lapse_count=memory.lapse_count + lapsed,
        state=state,
    )


def replay(scheduler: MemoryScheduler, reviews: Iterable[tuple[int, datetime]]) -> CardMemory:
    """Rebuild a card's memory from its review history (grade, time), oldest first.

    Used when a card switches to another scheduler or when review history is imported.
    """
    memory = CardMemory()
    for grade, reviewed_at in reviews:
        memory = scheduler.review(memory, grade, reviewed_at)
    return memory

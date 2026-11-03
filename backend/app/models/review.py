from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UTCDateTime

REVIEW_STATUSES = ("new", "learning", "review", "relearning")


class ReviewState(Base):
    """Where a card currently stands in its schedule: exactly one row per card.

    The columns here are the ones every scheduler provides, so other parts of the app
    (session building, notifications) never depend on a particular scheduling algorithm.
    Anything specific to one algorithm lives in scheduler_state as JSON.
    """

    __tablename__ = "review_states"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in REVIEW_STATUSES)})", name="status"
        ),
        CheckConstraint("ISJSON(scheduler_state) = 1", name="scheduler_state_json"),
    )

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    # new = never studied; learning / relearning = short steps after learning or forgetting;
    # review = long-term intervals
    status: Mapped[str] = mapped_column(Unicode(10), default="new")
    # NULL while the card is new; indexed because "what is due now?" is the most frequent query
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    review_count: Mapped[int] = mapped_column(default=0)
    lapse_count: Mapped[int] = mapped_column(default=0)
    # Which scheduler owns this card, e.g. "fsrs" or "fixed_steps"
    scheduler: Mapped[str] = mapped_column(Unicode(50), default="fsrs")
    # That scheduler's private data as JSON, e.g. {"stability": 2.3, "difficulty": 5.1}
    scheduler_state: Mapped[str | None] = mapped_column(Unicode())

    card: Mapped["Card"] = relationship(back_populates="review_state")  # noqa: F821


class Review(Base):
    """One review attempt. Rows are only ever added, never changed: this is the full history."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("grade BETWEEN 1 AND 4", name="grade"),
        Index("ix_reviews_card_id_reviewed_at", "card_id", "reviewed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    # The meaning of each grade (e.g. 1 = Again ... 4 = Easy) is defined by the scheduler config.
    grade: Mapped[int] = mapped_column(SmallInteger)
    # How long the answer took, in milliseconds (NULL if unknown)
    duration_ms: Mapped[int | None] = mapped_column()
    next_due_at: Mapped[datetime] = mapped_column(UTCDateTime())
    # What decided next_due_at, e.g. "fsrs" or "anki-import"
    scheduler: Mapped[str] = mapped_column(Unicode(50))

    card: Mapped["Card"] = relationship(back_populates="reviews")  # noqa: F821

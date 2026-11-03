from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UTCDateTime

REVIEW_STATUSES = ("new", "learning", "review")


class ReviewState(Base):
    """Where a card currently stands in its schedule: exactly one row per card.

    This is a fast-to-query summary of the card's review history. It is updated in
    place after every review, while the history itself is kept in the reviews table.
    """

    __tablename__ = "review_states"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in REVIEW_STATUSES)})", name="status"
        ),
    )

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    # new = created but never studied; learning = hour-scale steps; review = day-scale steps
    status: Mapped[str] = mapped_column(Unicode(10), default="new")
    step: Mapped[int] = mapped_column(SmallInteger, default=0)
    # NULL while the card is new; indexed because "what is due now?" is the most frequent query
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    review_count: Mapped[int] = mapped_column(default=0)
    lapse_count: Mapped[int] = mapped_column(default=0)

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
    next_due_at: Mapped[datetime] = mapped_column(UTCDateTime())
    scheduler_version: Mapped[str] = mapped_column(Unicode(20))

    card: Mapped["Card"] = relationship(back_populates="reviews")  # noqa: F821

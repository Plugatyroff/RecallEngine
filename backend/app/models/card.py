from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UTCDateTime, utc_now

CARD_KINDS = ("basic", "definition", "theorem", "proof", "application", "vocab")


class Card(Base):
    """A flashcard. front and back hold Markdown text (LaTeX math such as $x^2$ is allowed)."""

    __tablename__ = "cards"
    __table_args__ = (
        CheckConstraint(f"kind IN ({', '.join(repr(k) for k in CARD_KINDS)})", name="kind"),
        CheckConstraint("priority BETWEEN 1 AND 3", name="priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    front: Mapped[str] = mapped_column(Unicode())  # NVARCHAR(MAX)
    back: Mapped[str] = mapped_column(Unicode())  # NVARCHAR(MAX)
    kind: Mapped[str] = mapped_column(Unicode(20), default="basic")
    # 1 = low, 2 = normal, 3 = high
    priority: Mapped[int] = mapped_column(SmallInteger, default=2)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    topic: Mapped["Topic"] = relationship(back_populates="cards")  # noqa: F821
    review_state: Mapped["ReviewState"] = relationship(  # noqa: F821
        back_populates="card", cascade="all, delete-orphan", passive_deletes=True
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        back_populates="card", cascade="all, delete-orphan", passive_deletes=True
    )

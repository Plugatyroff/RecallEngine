from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UTCDateTime, utc_now
from app.models.note import unique_when_set


class Card(Base):
    """One reviewable card: a note shown through one of its note type's templates.

    The content lives in the note; the card only records which template it uses and which
    topic it belongs to (like Anki, sibling cards of one note may sit in different topics).
    """

    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("note_id", "template_ord"),
        unique_when_set("ix_cards_anki_id", "anki_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    # Which template of the note type produces this card (NoteTypeTemplate.ord)
    template_ord: Mapped[int] = mapped_column(SmallInteger, default=0)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    anki_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    note: Mapped["Note"] = relationship(back_populates="cards")  # noqa: F821
    topic: Mapped["Topic"] = relationship(back_populates="cards")  # noqa: F821
    review_state: Mapped["ReviewState"] = relationship(  # noqa: F821
        back_populates="card", cascade="all, delete-orphan", passive_deletes=True
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        back_populates="card", cascade="all, delete-orphan", passive_deletes=True
    )

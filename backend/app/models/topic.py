from datetime import datetime

from sqlalchemy import ForeignKey, Unicode, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UTCDateTime, utc_now


class Topic(Base):
    """A subject or subtopic. Topics form a tree through parent_id.

    Top-level topics (the main menu) have parent_id = NULL. Deleting a topic is not
    cascaded to its subtopics or cards: the database refuses to delete a topic that
    still contains anything.
    """

    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("parent_id", "name"),)  # no duplicate names among siblings

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), index=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    parent: Mapped["Topic | None"] = relationship(back_populates="children", remote_side=[id])
    children: Mapped[list["Topic"]] = relationship(back_populates="parent")
    cards: Mapped[list["Card"]] = relationship(back_populates="topic")  # noqa: F821

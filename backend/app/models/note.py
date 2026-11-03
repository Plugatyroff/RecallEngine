"""Notes hold the content; note types define which fields a note has and which cards it produces.

This follows Anki's model so Anki collections can be imported without losing structure:
a "Basic (and reversed)" note type has fields Front and Back and two templates, so each of its
notes produces two cards (Front -> Back and Back -> Front) that share the same content.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    SmallInteger,
    Table,
    Unicode,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import UTCDateTime, utc_now

NOTE_KINDS = ("basic", "definition", "theorem", "proof", "application", "vocab")


def unique_when_set(name: str, column: str) -> Index:
    """A unique index that ignores NULLs.

    A plain UNIQUE constraint in SQL Server allows only one NULL per column, but most rows
    have no Anki ID at all, so the index only covers rows where the ID is set.
    """
    return Index(name, column, unique=True, mssql_where=text(f"{column} IS NOT NULL"))


class NoteType(Base):
    """Defines the fields of a note (e.g. Spanish, Picture, English) and its card templates."""

    __tablename__ = "note_types"
    __table_args__ = (
        CheckConstraint("ISJSON(fields) = 1", name="fields_json"),
        unique_when_set("ix_note_types_anki_id", "anki_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(200), unique=True)
    # Field names in order, as a JSON list: ["Front", "Back"]
    fields: Mapped[str] = mapped_column(Unicode())
    anki_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    templates: Mapped[list["NoteTypeTemplate"]] = relationship(
        back_populates="note_type",
        order_by="NoteTypeTemplate.ord",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notes: Mapped[list["Note"]] = relationship(back_populates="note_type")


class NoteTypeTemplate(Base):
    """One card template of a note type. Each note gets one card per template.

    Templates use Anki's syntax: {{Field}} inserts a field, {{FrontSide}} repeats the front
    on the back, and {{#Field}}...{{/Field}} is only shown when the field is not empty.
    """

    __tablename__ = "note_type_templates"
    __table_args__ = (UniqueConstraint("note_type_id", "ord"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    note_type_id: Mapped[int] = mapped_column(ForeignKey("note_types.id", ondelete="CASCADE"))
    # Position within the note type: 0, 1, ... Cards refer to their template by this number.
    ord: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(Unicode(200))
    front_template: Mapped[str] = mapped_column(Unicode())
    back_template: Mapped[str] = mapped_column(Unicode())

    note_type: Mapped["NoteType"] = relationship(back_populates="templates")


note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(200), unique=True)

    notes: Mapped[list["Note"]] = relationship(secondary=note_tags, back_populates="tags")


class Note(Base):
    """The content of one or more cards. Field values are stored as HTML.

    Deleting a note deletes its cards. A note type that is still used by notes cannot be deleted.
    """

    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("ISJSON(fields) = 1", name="fields_json"),
        CheckConstraint(f"kind IN ({', '.join(repr(k) for k in NOTE_KINDS)})", name="kind"),
        CheckConstraint("priority BETWEEN 1 AND 3", name="priority"),
        unique_when_set("ix_notes_anki_guid", "anki_guid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note_type_id: Mapped[int] = mapped_column(ForeignKey("note_types.id"), index=True)
    # Field values in the same order as the note type's field names, as a JSON list of HTML strings
    fields: Mapped[str] = mapped_column(Unicode())
    kind: Mapped[str] = mapped_column(Unicode(20), default="basic")
    # 1 = low, 2 = normal, 3 = high
    priority: Mapped[int] = mapped_column(SmallInteger, default=2)
    # Anki's permanent note ID, so re-importing a deck updates notes instead of duplicating them
    anki_guid: Mapped[str | None] = mapped_column(Unicode(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    note_type: Mapped["NoteType"] = relationship(back_populates="notes")
    cards: Mapped[list["Card"]] = relationship(  # noqa: F821
        back_populates="note", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list["Tag"]] = relationship(secondary=note_tags, back_populates="notes")

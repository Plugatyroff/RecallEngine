"""Creating notes and turning cards into displayable HTML."""

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Card, Note, NoteType, ReviewState, Tag, Topic
from app.services.errors import InvalidInputError, NotFoundError
from app.services.queue import with_content
from app.services.scheduling import DEFAULT_SCHEDULER
from app.services.templates import front_is_empty, render, strip_html


@dataclass(frozen=True)
class RenderedCard:
    front: str
    back: str


def field_names(note_type: NoteType) -> list[str]:
    return json.loads(note_type.fields)


def note_fields(note: Note) -> dict[str, str]:
    return dict(zip(field_names(note.note_type), json.loads(note.fields)))


def render_card(card: Card) -> RenderedCard:
    template = next(t for t in card.note.note_type.templates if t.ord == card.template_ord)
    fields = note_fields(card.note)
    front = render(template.front_template, fields)
    return RenderedCard(front=front, back=render(template.back_template, fields, front_side=front))


def preview(card: Card, length: int = 80) -> str:
    """Short plain-text version of a card's front, for lists."""
    text = strip_html(render_card(card).front)
    return text if len(text) <= length else text[: length - 1] + "…"


def list_note_types(session: Session) -> list[NoteType]:
    return list(session.scalars(select(NoteType).options(selectinload(NoteType.templates)).order_by(NoteType.name)))


def get_basic_note_type(session: Session) -> NoteType:
    note_type = session.scalar(select(NoteType).where(NoteType.name == "Basic"))
    if note_type is None:
        raise NotFoundError("The 'Basic' note type is missing")
    return note_type


def create_note(
    session: Session,
    *,
    topic_id: int,
    fields: list[str],
    note_type_id: int | None = None,
    kind: str = "basic",
    priority: int = 2,
    tags: list[str] = (),
) -> Note:
    """Create a note and one card per template whose front is not empty (as Anki does)."""
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise NotFoundError(f"Topic {topic_id} not found")
    note_type = session.get(NoteType, note_type_id) if note_type_id is not None else get_basic_note_type(session)
    if note_type is None:
        raise NotFoundError(f"Note type {note_type_id} not found")

    names = field_names(note_type)
    if len(fields) != len(names):
        raise InvalidInputError(f"Note type {note_type.name!r} has {len(names)} fields {names}, got {len(fields)}")

    # Load everything needed from the database before building the new objects
    templates = list(note_type.templates)
    note_tags = [_tag(session, name) for name in dict.fromkeys(tags)]

    note = Note(note_type=note_type, fields=json.dumps(fields, ensure_ascii=False), kind=kind,
                priority=priority, tags=note_tags)
    values = dict(zip(names, fields))
    for template in templates:
        if front_is_empty(render(template.front_template, values)):
            continue
        card = Card(template_ord=template.ord, topic=topic)
        card.review_state = ReviewState(scheduler=DEFAULT_SCHEDULER)
        note.cards.append(card)
    if not note.cards:
        raise InvalidInputError("These fields produce no cards: every card's front would be empty")

    session.add(note)
    session.flush()
    return note


def get_card(session: Session, card_id: int) -> Card:
    card = session.scalar(select(Card).where(Card.id == card_id).options(*with_content()))
    if card is None:
        raise NotFoundError(f"Card {card_id} not found")
    return card


def list_cards_in_topic(session: Session, topic_id: int) -> list[Card]:
    if session.get(Topic, topic_id) is None:
        raise NotFoundError(f"Topic {topic_id} not found")
    return list(session.scalars(
        select(Card).where(Card.topic_id == topic_id).options(*with_content()).order_by(Card.id)
    ))


def _tag(session: Session, name: str) -> Tag:
    name = name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == name))
    return tag or Tag(name=name)

"""Reading, creating and deleting topics."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, delete, exists, func, select, update
from sqlalchemy.orm import Session

from app.models import Card, Note, ReviewState, Topic
from app.services.errors import InvalidInputError, NotFoundError


@dataclass(frozen=True)
class TopicSummary:
    id: int
    parent_id: int | None
    name: str
    card_count: int  # cards directly in this topic, not in its subtopics
    due_count: int


def list_topics(session: Session, now: datetime) -> list[TopicSummary]:
    """All topics with their card counts, as a flat list; parent_id describes the tree."""
    is_due = case((ReviewState.due_at <= now, 1), else_=0)
    counts = (
        select(Card.topic_id, func.count(Card.id).label("cards"), func.sum(is_due).label("due"))
        .join(ReviewState, ReviewState.card_id == Card.id)
        .group_by(Card.topic_id)
        .subquery()
    )
    rows = session.execute(
        select(Topic.id, Topic.parent_id, Topic.name, counts.c.cards, counts.c.due)
        .outerjoin(counts, counts.c.topic_id == Topic.id)
        .order_by(Topic.name)
    )
    return [
        TopicSummary(id=row.id, parent_id=row.parent_id, name=row.name,
                     card_count=row.cards or 0, due_count=row.due or 0)
        for row in rows
    ]


def subtree_ids(session: Session, topic_id: int) -> list[int]:
    """The topic and all topics below it, at any depth."""
    if session.get(Topic, topic_id) is None:
        raise NotFoundError(f"Topic {topic_id} not found")
    children: dict[int | None, list[int]] = {}
    for id_, parent_id in session.execute(select(Topic.id, Topic.parent_id)):
        children.setdefault(parent_id, []).append(id_)
    result, pending = [], [topic_id]
    while pending:
        current = pending.pop()
        result.append(current)
        pending.extend(children.get(current, []))
    return result


def create_topic(session: Session, name: str, parent_id: int | None) -> Topic:
    name = name.strip()
    if not name:
        raise InvalidInputError("Topic name must not be empty")
    if parent_id is not None and session.get(Topic, parent_id) is None:
        raise NotFoundError(f"Topic {parent_id} not found")
    duplicate = session.scalar(select(Topic.id).where(Topic.parent_id == parent_id, Topic.name == name))
    if duplicate is not None:
        raise InvalidInputError(f"A topic called {name!r} already exists here")
    topic = Topic(name=name, parent_id=parent_id)
    session.add(topic)
    session.flush()
    return topic


@dataclass(frozen=True)
class DeletedTopic:
    topics: int
    cards: int
    notes: int


def delete_topic(session: Session, topic_id: int) -> DeletedTopic:
    """Delete a topic with all its subtopics and their cards, including the cards' review history.

    A note is deleted when all of its cards were in the deleted topics. A note with a sibling card
    in another topic is kept, together with that card.
    """
    topic_ids = subtree_ids(session, topic_id)
    in_subtree = Card.topic_id.in_(topic_ids)
    # Notes whose cards are all in the subtree
    only_here = Note.id.in_(select(Card.note_id).where(in_subtree)) & ~exists(
        select(Card.id).where(Card.note_id == Note.id, ~in_subtree)
    )
    card_count = session.scalar(select(func.count()).select_from(Card).where(in_subtree))
    note_count = session.scalar(select(func.count()).select_from(Note).where(only_here))

    # The database deletes each card's review state and reviews along with the card (ON DELETE
    # CASCADE), and each note's cards and tag links along with the note.
    session.execute(delete(Note).where(only_here), execution_options={"synchronize_session": False})
    session.execute(delete(Card).where(in_subtree), execution_options={"synchronize_session": False})
    # Topics refer to their parents, so detach them before deleting the whole subtree at once
    session.execute(update(Topic).where(Topic.id.in_(topic_ids)).values(parent_id=None),
                    execution_options={"synchronize_session": False})
    session.execute(delete(Topic).where(Topic.id.in_(topic_ids)), execution_options={"synchronize_session": False})
    session.expire_all()
    return DeletedTopic(topics=len(topic_ids), cards=card_count, notes=note_count)

"""Reading and creating topics."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Card, ReviewState, Topic
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

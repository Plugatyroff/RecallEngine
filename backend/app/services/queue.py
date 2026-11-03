"""Which cards to review now.

This is a deliberately simple first version: cards that are due, most overdue first, followed by
a limited number of new cards. It will be replaced by the session builder, which also mixes
subjects, brings back neglected topics and respects priorities (see docs/scheduling.md).
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Card, Note, NoteType, ReviewState


def with_content():
    """Load options for everything needed to display a card."""
    return (
        selectinload(Card.review_state),
        selectinload(Card.topic),
        selectinload(Card.note).selectinload(Note.note_type).selectinload(NoteType.templates),
    )


def review_queue(
    session: Session,
    now: datetime,
    limit: int = 50,
    new_limit: int = 10,
    topic_ids: Sequence[int] | None = None,
) -> list[Card]:
    """Due cards first, then up to new_limit new cards; only from topic_ids if given."""

    def cards_where(*conditions):
        query = select(Card).join(ReviewState, ReviewState.card_id == Card.id).where(*conditions)
        if topic_ids is not None:
            query = query.where(Card.topic_id.in_(topic_ids))
        return query.options(*with_content())

    due = list(session.scalars(cards_where(ReviewState.due_at <= now).order_by(ReviewState.due_at).limit(limit)))
    room_for_new = min(new_limit, limit - len(due))
    if room_for_new <= 0:
        return due
    new = session.scalars(cards_where(ReviewState.status == "new").order_by(Card.id).limit(room_for_new))
    return due + list(new)

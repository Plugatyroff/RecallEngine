"""Which cards to review now.

This is a deliberately simple first version: cards that are due, most overdue first, followed by
a limited number of new cards. It will be replaced by the session builder, which also mixes
subjects, brings back neglected topics and respects priorities (see docs/scheduling.md).
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Card, Note, NoteType, ReviewState


def _with_content():
    return (
        selectinload(Card.review_state),
        selectinload(Card.topic),
        selectinload(Card.note).selectinload(Note.note_type).selectinload(NoteType.templates),
    )


def review_queue(session: Session, now: datetime, limit: int = 50, new_limit: int = 10) -> list[Card]:
    due = list(session.scalars(
        select(Card)
        .join(ReviewState, ReviewState.card_id == Card.id)
        .where(ReviewState.due_at <= now)
        .order_by(ReviewState.due_at)
        .limit(limit)
        .options(*_with_content())
    ))
    room_for_new = min(new_limit, limit - len(due))
    if room_for_new <= 0:
        return due
    new = session.scalars(
        select(Card)
        .join(ReviewState, ReviewState.card_id == Card.id)
        .where(ReviewState.status == "new")
        .order_by(Card.id)
        .limit(room_for_new)
        .options(*_with_content())
    )
    return due + list(new)

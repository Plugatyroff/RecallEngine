"""The HTTP endpoints. They only translate between JSON and the services."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import schemas
from app.api.deps import get_now, get_session
from app.services import notes, queue, reviews, topics
from app.services.errors import InvalidInputError, NotFoundError

router = APIRouter(prefix="/api/v1")

SessionDep = Annotated[Session, Depends(get_session)]
NowDep = Annotated[datetime, Depends(get_now)]


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(error))
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.get("/topics", response_model=list[schemas.TopicOut])
def list_topics(session: SessionDep, now: NowDep):
    """All topics as a flat list; build the tree from parent_id."""
    return topics.list_topics(session, now)


@router.post("/topics", response_model=schemas.TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(body: schemas.TopicCreate, session: SessionDep):
    try:
        topic = topics.create_topic(session, body.name, body.parent_id)
    except (NotFoundError, InvalidInputError) as error:
        raise _http_error(error)
    return schemas.TopicOut(id=topic.id, parent_id=topic.parent_id, name=topic.name, card_count=0, due_count=0)


@router.get("/topics/{topic_id}/cards", response_model=list[schemas.CardSummary])
def list_cards(topic_id: int, session: SessionDep):
    try:
        cards = notes.list_cards_in_topic(session, topic_id)
    except NotFoundError as error:
        raise _http_error(error)
    return [
        schemas.CardSummary(id=c.id, note_id=c.note_id, preview=notes.preview(c),
                            status=c.review_state.status, due_at=c.review_state.due_at)
        for c in cards
    ]


@router.get("/note-types", response_model=list[schemas.NoteTypeOut])
def list_note_types(session: SessionDep):
    return [
        schemas.NoteTypeOut(id=t.id, name=t.name, fields=notes.field_names(t),
                            templates=[template.name for template in t.templates])
        for t in notes.list_note_types(session)
    ]


@router.post("/notes", response_model=schemas.NoteCreated, status_code=status.HTTP_201_CREATED)
def create_note(body: schemas.NoteCreate, session: SessionDep):
    """Create a note; its cards are created automatically, one per template."""
    try:
        note = notes.create_note(session, topic_id=body.topic_id, fields=body.fields,
                                 note_type_id=body.note_type_id, kind=body.kind,
                                 priority=body.priority, tags=body.tags)
    except (NotFoundError, InvalidInputError) as error:
        raise _http_error(error)
    return schemas.NoteCreated(id=note.id, card_ids=[c.id for c in note.cards])


@router.get("/cards/{card_id}", response_model=schemas.CardDetail)
def get_card(card_id: int, session: SessionDep, now: NowDep):
    try:
        card = notes.get_card(session, card_id)
    except NotFoundError as error:
        raise _http_error(error)
    rendered, state = notes.render_card(card), card.review_state
    return schemas.CardDetail(
        id=card.id, note_id=card.note_id, topic_id=card.topic_id, topic_name=card.topic.name,
        status=state.status, due_at=state.due_at, last_reviewed_at=state.last_reviewed_at,
        review_count=state.review_count, lapse_count=state.lapse_count,
        front_html=rendered.front, back_html=rendered.back,
        next_due_by_grade=reviews.next_due_by_grade(card, now),
    )


@router.get("/review/queue", response_model=schemas.ReviewQueue)
def review_queue(
    session: SessionDep,
    now: NowDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    new_limit: Annotated[int, Query(ge=0, le=200)] = 10,
    topic_id: Annotated[int | None, Query(description="Only this topic and its subtopics")] = None,
):
    """Cards to review now: due cards first, then up to new_limit new cards."""
    try:
        topic_ids = topics.subtree_ids(session, topic_id) if topic_id is not None else None
    except NotFoundError as error:
        raise _http_error(error)
    cards = []
    for card in queue.review_queue(session, now, limit=limit, new_limit=new_limit, topic_ids=topic_ids):
        rendered = notes.render_card(card)
        cards.append(schemas.CardToReview(
            id=card.id, topic_id=card.topic_id, topic_name=card.topic.name,
            status=card.review_state.status, front_html=rendered.front, back_html=rendered.back,
            next_due_by_grade=reviews.next_due_by_grade(card, now),
        ))
    return schemas.ReviewQueue(cards=cards)


@router.post("/cards/{card_id}/reviews", response_model=schemas.ReviewResult)
def submit_review(card_id: int, body: schemas.ReviewSubmit, session: SessionDep, now: NowDep):
    """Record a review; the review time is the server's current time."""
    try:
        card = reviews.submit_review(session, card_id, body.grade, now, body.duration_ms)
    except NotFoundError as error:
        raise _http_error(error)
    return schemas.ReviewResult(card_id=card.id, status=card.review_state.status, due_at=card.review_state.due_at)

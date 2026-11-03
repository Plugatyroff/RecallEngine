"""The shapes of JSON sent to and from the API (validated by Pydantic)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.note import NOTE_KINDS


class TopicOut(BaseModel):
    id: int
    parent_id: int | None
    name: str
    card_count: int
    due_count: int


class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: int | None = None


class NoteTypeOut(BaseModel):
    id: int
    name: str
    fields: list[str]
    templates: list[str]


class NoteCreate(BaseModel):
    topic_id: int
    # Field values in the note type's order; HTML is allowed
    fields: list[str] = Field(min_length=1)
    note_type_id: int | None = Field(default=None, description="Defaults to the Basic note type")
    kind: str = Field(default="basic", pattern=f"^({'|'.join(NOTE_KINDS)})$")
    priority: int = Field(default=2, ge=1, le=3)
    tags: list[str] = []


class NoteCreated(BaseModel):
    id: int
    card_ids: list[int]


class CardSummary(BaseModel):
    id: int
    note_id: int
    preview: str
    status: str
    due_at: datetime | None


class CardDetail(BaseModel):
    id: int
    note_id: int
    topic_id: int
    topic_name: str
    status: str
    due_at: datetime | None
    last_reviewed_at: datetime | None
    review_count: int
    lapse_count: int
    front_html: str
    back_html: str
    # When the card would come back if reviewed now, for each grade (1 = Again ... 4 = Easy)
    next_due_by_grade: dict[int, datetime]


class CardToReview(BaseModel):
    id: int
    topic_id: int
    topic_name: str
    status: str
    front_html: str
    back_html: str
    # When the card would come back for each grade (1 = Again ... 4 = Easy)
    next_due_by_grade: dict[int, datetime]


class ReviewQueue(BaseModel):
    cards: list[CardToReview]


class ReviewSubmit(BaseModel):
    grade: int = Field(ge=1, le=4)
    duration_ms: int | None = Field(default=None, ge=0)


class ReviewResult(BaseModel):
    card_id: int
    status: str
    due_at: datetime

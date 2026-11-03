"""Tests for the HTTP endpoints, run against the test database."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_now, get_session
from app.main import app

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> dict[str, datetime]:
    return {"now": NOW}


@pytest.fixture
def client(session: Session, clock: dict[str, datetime]) -> Iterator[TestClient]:
    """An API client using the test database session (rolled back after each test) and a fake clock."""
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_now] = lambda: clock["now"]
    yield TestClient(app)
    app.dependency_overrides.clear()


def create_topic(client: TestClient, name: str, parent_id: int | None = None) -> dict:
    response = client.post("/api/v1/topics", json={"name": name, "parent_id": parent_id})
    assert response.status_code == 201, response.text
    return response.json()


def create_note(client: TestClient, topic_id: int, fields: list[str], **extra) -> dict:
    response = client.post("/api/v1/notes", json={"topic_id": topic_id, "fields": fields, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_topics_are_listed_with_their_parent_and_counts(client: TestClient) -> None:
    hungarian = create_topic(client, "Hungarian")
    vocab = create_topic(client, "Vocabulary", hungarian["id"])
    create_note(client, vocab["id"], ["alma", "apple"])

    topics = {t["name"]: t for t in client.get("/api/v1/topics").json()}

    assert topics["Vocabulary"]["parent_id"] == hungarian["id"]
    assert topics["Vocabulary"]["card_count"] == 1
    assert topics["Hungarian"]["card_count"] == 0


def test_duplicate_or_orphan_topics_are_rejected(client: TestClient) -> None:
    create_topic(client, "Hungarian")

    assert client.post("/api/v1/topics", json={"name": "Hungarian"}).status_code == 422
    assert client.post("/api/v1/topics", json={"name": "X", "parent_id": 999999}).status_code == 404


def test_note_types_include_basic(client: TestClient) -> None:
    basic = next(t for t in client.get("/api/v1/note-types").json() if t["name"] == "Basic")

    assert basic["fields"] == ["Front", "Back"]
    assert basic["templates"] == ["Card 1"]


def test_creating_a_note_creates_its_cards(client: TestClient) -> None:
    topic = create_topic(client, "Hungarian")

    note = create_note(client, topic["id"], ["alma", "<b>apple</b>"], tags=["A1"])
    cards = client.get(f"/api/v1/topics/{topic['id']}/cards").json()

    assert [c["id"] for c in cards] == note["card_ids"]
    assert cards[0]["preview"] == "alma"
    assert cards[0]["status"] == "new"


@pytest.mark.parametrize(
    "body, expected",
    [
        ({"topic_id": 999999, "fields": ["a", "b"]}, 404),
        ({"fields": ["only one field"]}, 422),
        ({"fields": ["", "back"]}, 422),  # empty front: no card would be created
        ({"fields": ["a", "b"], "priority": 7}, 422),
        ({"fields": ["a", "b"], "kind": "poem"}, 422),
    ],
)
def test_invalid_notes_are_rejected(client: TestClient, body: dict, expected: int) -> None:
    topic = create_topic(client, "Hungarian")

    response = client.post("/api/v1/notes", json={"topic_id": topic["id"], **body})

    assert response.status_code == expected


def test_review_loop(client: TestClient, clock: dict) -> None:
    """Create a card, review it, and see when it is next due: the Phase 1 success criterion."""
    topic = create_topic(client, "Hungarian")
    create_note(client, topic["id"], ["alma", "apple"])

    queue = client.get("/api/v1/review/queue").json()["cards"]
    assert len(queue) == 1
    card = queue[0]
    assert card["front_html"] == "alma"
    assert "apple" in card["back_html"]
    good_due = datetime.fromisoformat(card["next_due_by_grade"]["3"])

    result = client.post(f"/api/v1/cards/{card['id']}/reviews", json={"grade": 3, "duration_ms": 2500}).json()

    assert datetime.fromisoformat(result["due_at"]) == good_due
    assert result["status"] == "review"
    assert client.get("/api/v1/review/queue").json()["cards"] == []  # not due yet

    clock["now"] = good_due + timedelta(minutes=1)
    assert [c["id"] for c in client.get("/api/v1/review/queue").json()["cards"]] == [card["id"]]


def test_queue_puts_due_cards_before_new_ones_and_limits_new_cards(client: TestClient, clock: dict) -> None:
    topic = create_topic(client, "Hungarian")
    first = create_note(client, topic["id"], ["first", "1"])["card_ids"][0]
    for i in range(3):
        create_note(client, topic["id"], [f"new {i}", "x"])
    client.post(f"/api/v1/cards/{first}/reviews", json={"grade": 1})
    clock["now"] = NOW + timedelta(hours=1)

    queue = client.get("/api/v1/review/queue", params={"new_limit": 2}).json()["cards"]

    assert queue[0]["id"] == first
    assert queue[0]["status"] == "learning"
    assert len(queue) == 3


def test_a_card_can_be_opened(client: TestClient) -> None:
    topic = create_topic(client, "Hungarian")
    card_id = create_note(client, topic["id"], ["alma", "apple"])["card_ids"][0]

    card = client.get(f"/api/v1/cards/{card_id}").json()

    assert (card["front_html"], card["topic_name"], card["status"]) == ("alma", "Hungarian", "new")
    assert "apple" in card["back_html"]
    assert client.get("/api/v1/cards/999999").status_code == 404


def test_queue_can_be_limited_to_a_topic_and_its_subtopics(client: TestClient) -> None:
    hungarian = create_topic(client, "Hungarian")
    vocab = create_topic(client, "Vocabulary", hungarian["id"])
    words = create_topic(client, "Food", vocab["id"])
    maths = create_topic(client, "Mathematics")
    in_hungarian = [
        create_note(client, hungarian["id"], ["a", "b"])["card_ids"][0],
        create_note(client, words["id"], ["alma", "apple"])["card_ids"][0],
    ]
    create_note(client, maths["id"], ["1+1", "2"])

    def queue(**params) -> list[int]:
        return [c["id"] for c in client.get("/api/v1/review/queue", params=params).json()["cards"]]

    assert queue(topic_id=hungarian["id"]) == in_hungarian
    assert queue(topic_id=words["id"]) == in_hungarian[1:]
    assert len(queue()) == 3
    assert client.get("/api/v1/review/queue", params={"topic_id": 999999}).status_code == 404


def test_reviewing_requires_a_valid_grade_and_card(client: TestClient) -> None:
    topic = create_topic(client, "Hungarian")
    card_id = create_note(client, topic["id"], ["alma", "apple"])["card_ids"][0]

    assert client.post(f"/api/v1/cards/{card_id}/reviews", json={"grade": 5}).status_code == 422
    assert client.post("/api/v1/cards/999999/reviews", json={"grade": 3}).status_code == 404

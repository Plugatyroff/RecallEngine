"""Fill the database with fake topics, cards and review history for development.

Usage (from the backend folder, with the virtual environment active):
    python scripts/seed.py            # only runs if the database is empty
    python scripts/seed.py --reset    # deletes ALL existing data first

Never use --reset once the database holds real cards you want to keep.
"""

import argparse
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models import Card, Review, ReviewState, Topic

NOW = datetime.now(UTC)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)

# topic path -> list of (front, back, kind)
CARDS: dict[tuple[str, ...], list[tuple[str, str, str]]] = {
    ("Mathematics", "Linear Algebra", "Matrices", "Determinants"): [
        ("What is the determinant of a 2×2 matrix $\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$?",
         "$ad - bc$", "definition"),
        ("State the product rule for determinants.", "$\\det(AB) = \\det(A)\\det(B)$", "theorem"),
        ("When is a square matrix invertible?", "Exactly when $\\det(A) \\neq 0$.", "theorem"),
    ],
    ("Mathematics", "Linear Algebra", "Matrices", "Matrix Operations"): [
        ("When can matrices $A$ and $B$ be multiplied as $AB$?",
         "When the number of columns of $A$ equals the number of rows of $B$.", "definition"),
        ("Is matrix multiplication commutative?", "No: in general $AB \\neq BA$.", "basic"),
    ],
    ("Mathematics", "Calculus", "Derivatives"): [
        ("Define the derivative of $f$ at $x$.",
         "$f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}$", "definition"),
        ("Differentiate $x^n$.", "$n x^{n-1}$", "application"),
    ],
    ("Hungarian", "Vocabulary"): [
        ("alma", "apple", "vocab"),
        ("kutya", "dog", "vocab"),
        ("ház", "house", "vocab"),
        ("könyv", "book", "vocab"),
        ("víz", "water", "vocab"),
        ("szőlő", "grapes", "vocab"),
    ],
    ("Hungarian", "Grammar"): [
        ("What does the suffix -ban/-ben express?", "Being inside something: *a házban* = in the house.",
         "basic"),
    ],
    ("Electronics", "Microcontrollers"): [
        ("What does GPIO stand for?", "General-Purpose Input/Output", "definition"),
        ("What is a pull-up resistor for?",
         "It holds an input pin at a defined high level when nothing drives it.", "basic"),
    ],
    ("Electronics", "Digital Electronics"): [
        ("What is the output of a NAND gate when both inputs are 1?", "0", "basic"),
    ],
}

# A few example schedules, applied to cards in turn, so the data shows every state:
# (status, step, due_at, review history as (time ago, grade))
EXAMPLE_STATES = [
    ("new", 0, None, []),
    ("learning", 0, NOW + 1 * HOUR, [(1 * HOUR, 3)]),
    ("learning", 1, NOW - 30 * timedelta(minutes=1), [(8 * HOUR, 3), (6 * HOUR + 30 * timedelta(minutes=1), 3)]),
    ("learning", 0, NOW - 10 * timedelta(minutes=1), [(3 * HOUR, 3), (2 * HOUR, 1)]),
    ("review", 3, NOW + 2 * DAY, [(3 * DAY, 3), (3 * DAY - 2 * HOUR, 3), (2 * DAY, 4), (1 * DAY, 3)]),
]


def reset(session: Session) -> None:
    session.execute(delete(Review))
    session.execute(delete(ReviewState))
    session.execute(delete(Card))
    # Topics reference each other, so detach them from their parents before deleting.
    session.execute(update(Topic).values(parent_id=None))
    session.execute(delete(Topic))


def get_topic(session: Session, path: tuple[str, ...], cache: dict) -> Topic:
    """Return the topic at this path, creating it and any missing parents."""
    if path in cache:
        return cache[path]
    parent = get_topic(session, path[:-1], cache) if len(path) > 1 else None
    topic = Topic(name=path[-1], parent=parent)
    session.add(topic)
    cache[path] = topic
    return topic


def seed(session: Session) -> int:
    topics: dict[tuple[str, ...], Topic] = {}
    count = 0
    for path, cards in CARDS.items():
        topic = get_topic(session, path, topics)
        for front, back, kind in cards:
            status, step, due_at, history = EXAMPLE_STATES[count % len(EXAMPLE_STATES)]
            card = Card(topic=topic, front=front, back=back, kind=kind,
                        created_at=NOW - 4 * DAY, updated_at=NOW - 4 * DAY)
            card.review_state = ReviewState(
                status=status,
                step=step,
                due_at=due_at,
                last_reviewed_at=NOW - history[-1][0] if history else None,
                review_count=len(history),
                lapse_count=sum(1 for _, grade in history if grade == 1),
            )
            for i, (ago, grade) in enumerate(history):
                next_due = NOW - history[i + 1][0] if i + 1 < len(history) else due_at
                card.reviews.append(Review(reviewed_at=NOW - ago, grade=grade,
                                           next_due_at=next_due, scheduler_version="seed"))
            session.add(card)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete all existing data first")
    args = parser.parse_args()

    with SessionLocal.begin() as session:
        existing = session.scalar(select(func.count()).select_from(Topic))
        if existing and not args.reset:
            sys.exit(f"Database '{engine.url.database}' already has {existing} topics. "
                     "Use --reset to delete everything and re-seed.")
        if args.reset:
            reset(session)
        count = seed(session)

    print(f"Seeded {count} cards into '{engine.url.database}'.")


if __name__ == "__main__":
    main()

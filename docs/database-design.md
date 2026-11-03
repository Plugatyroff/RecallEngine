# Database design

Recall Engine stores its data in Microsoft SQL Server. The tables are defined as SQLAlchemy
models in [`backend/app/models/`](../backend/app/models/) and created by Alembic migrations in
[`backend/migrations/versions/`](../backend/migrations/versions/). Those files are the source of
truth; this document explains the reasoning behind them.

## Tables

```text
topics ──< topics           a topic has many subtopics (parent_id)
topics ──< cards            a topic has many cards (topic_id)
cards  ──  review_states    each card has exactly one scheduling state
cards  ──< reviews          each card has many review attempts
```

| Table | Purpose |
| --- | --- |
| `topics` | Subjects and subtopics, as one tree. `parent_id` is `NULL` for top-level topics (the main menu). |
| `cards` | Flashcard content: `front` and `back` as Markdown (LaTeX allowed), plus `kind` and `priority` (1–3). |
| `review_states` | Where each card stands in its schedule now: `status`, `step`, `due_at`, counters. Updated in place. |
| `reviews` | Every review attempt with its `grade` (1–4) and the resulting `next_due_at`. Rows are only added. |

## Decisions

**One self-referencing table for the topic hierarchy (adjacency list).** It supports any depth
with a single table. Children are a simple `WHERE parent_id = ?`; whole subtrees use a recursive
query. Alternatives such as SQL Server's `hierarchyid` or stored path strings only pay off for far
larger trees.

**Non-empty topics cannot be deleted.** SQL Server does not allow `ON DELETE CASCADE` on a
self-referencing foreign key, and a silent cascade could wipe out a whole subject anyway. The
foreign keys from `topics.parent_id` and `cards.topic_id` therefore make the database refuse to
delete a topic that still contains subtopics or cards.

**Scheduling state is separate from history.** `reviews` is the complete history and the source
of truth; `review_states` is a summary that makes "what is due now?" a single indexed lookup.
Keeping the full history allows replaying it through a different scheduler (e.g. FSRS) later.
Deleting a card cascades to both.

**Card content is separate from scheduling.** Editing a card never touches its schedule, and
changing the scheduler never touches card content.

**Grades are stored as numbers 1–4.** What each number means, and which buttons the app shows, is
configuration rather than database structure, so the grading scheme can change without a migration.

**`review_states.due_at` is `NULL` for new cards.** Creating a card is not the same as learning it:
a card only gets a due time after it is first studied.

## Conventions

- **Unicode text:** all text columns are `NVARCHAR`, so Hungarian accents and math symbols are stored correctly.
- **UTC timestamps:** all times are `DATETIME2` in UTC. The `UTCDateTime` column type converts on
  the way in and out and rejects datetimes without a time zone.
- **Named constraints:** a naming convention gives every key, index and constraint a predictable
  name (e.g. `fk_cards_topic_id_topics`), so migrations can refer to them.
- **Rules in the database:** `NOT NULL`, `CHECK` (grade, priority, kind, status), `UNIQUE` (sibling
  topic names) and foreign keys are enforced by SQL Server, not only by Python code.
- **Indexes** exist on the foreign keys and on `review_states.due_at`.

## Databases

| Database | Use |
| --- | --- |
| `RecallEngine` | Development data |
| `RecallEngine_test` | Automated tests; rebuilt from the migrations on every test run |

## Changing the schema

1. Edit the models in `backend/app/models/`.
2. `alembic revision --autogenerate -m "describe the change"` writes a migration file.
3. Read the generated file and adjust it if needed.
4. `alembic upgrade head` applies it. Commit the model change and the migration together.

Never change tables by hand in SSMS: the migrations would no longer match the database.

## Not yet implemented

`CardLink` (relationships between cards), `Tag` and `CardTag` are planned for Phase 2 and will be
added by migrations when a feature needs them.

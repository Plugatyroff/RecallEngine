# Database design

Recall Engine stores its data in Microsoft SQL Server. The tables are defined as SQLAlchemy
models in [`backend/app/models/`](../backend/app/models/) and created by Alembic migrations in
[`backend/migrations/versions/`](../backend/migrations/versions/). Those files are the source of
truth; this document explains the reasoning behind them.

## Tables

```text
note_types ──< note_type_templates     a note type defines fields and card templates
note_types ──< notes                   each note has a type
notes      ──< cards >── topics        a note produces one card per template; each card sits in a topic
topics     ──< topics                  topics form a tree (parent_id)
notes      >──< tags                   via note_tags
cards      ──  review_states           each card has exactly one scheduling state
cards      ──< reviews                 each card has many review attempts
```

| Table | Purpose |
| --- | --- |
| `topics` | Subjects and subtopics, as one tree. `parent_id` is `NULL` for top-level topics (the main menu). |
| `note_types` | A kind of note: its ordered field names (JSON list), e.g. `["Spanish", "Picture", "English", "Audio"]`. |
| `note_type_templates` | The card templates of a note type, in Anki's syntax (`{{Front}}`, `{{FrontSide}}`, `{{#Field}}…{{/Field}}`). |
| `notes` | The content: field values as a JSON list of HTML strings, plus `kind` and `priority` (1–3). |
| `cards` | One reviewable card = a note shown through one template (`template_ord`), placed in a topic. |
| `tags`, `note_tags` | Tags attached to notes. |
| `review_states` | Where each card stands in its schedule now. Updated in place. |
| `reviews` | Every review attempt with its `grade` (1–4), answer time and resulting `next_due_at`. Rows are only added. |

## Decisions

**Notes and cards are separate, as in Anki.** A "Basic (and reversed card)" note produces two cards
(front → back and back → front) that share one copy of the content, so editing the note updates
both. This keeps imported Anki collections intact: notes with several fields (e.g. Spanish word,
picture, English meaning, audio), reversed and optional-reverse cards, and sibling cards that
should not be shown back to back. `kind` and `priority` describe content, so they belong to the
note; the topic belongs to the card, because Anki allows siblings in different decks.

**Field values are HTML.** Anki stores HTML, so storing HTML avoids lossy conversions on import and
export. Media references (`<img src=…>`, `[sound:…]`) are kept as they are, so media support can be
added later without changing notes. HTML must be sanitized before display.

**Field values are one JSON list per note.** This mirrors Anki and keeps queries simple; SQL Server
can still search inside it (`JSON_VALUE`, `OPENJSON`). A `CHECK (ISJSON(fields) = 1)` constraint
rejects malformed values.

**Anki IDs for re-imports.** `note_types.anki_id`, `notes.anki_guid` and `cards.anki_id` remember
where an object came from, so importing the same collection again updates it instead of
duplicating it. They use *filtered* unique indexes (`WHERE … IS NOT NULL`), because a plain
`UNIQUE` constraint in SQL Server allows only one `NULL`, while most rows have no Anki ID.

**One self-referencing table for the topic hierarchy (adjacency list).** It supports any depth
with a single table. Children are a simple `WHERE parent_id = ?`; whole subtrees use a recursive
query. Anki deck names such as `Maths::Algebra::Matrices` map directly onto it.

**Non-empty topics and note types in use cannot be deleted.** SQL Server does not allow
`ON DELETE CASCADE` on a self-referencing foreign key, and a silent cascade could wipe out a whole
subject anyway. Deleting a note, on the other hand, deletes its cards and their review data.

**Scheduling state is generic.** `review_states` holds what every scheduler provides (`status`,
`due_at`, `last_reviewed_at`, counters) plus the name of the scheduler that owns the card and that
scheduler's private data as JSON (`scheduler_state`). Session building and notifications rely only
on the generic columns, so the scheduling algorithm (FSRS by default) can be replaced without
changing the database.

**History is separate from current state.** `reviews` is the complete history and the source of
truth; `review_states` is a summary that makes "what is due now?" a single indexed lookup. Keeping
the full history allows replaying it through a different scheduler later, including history
imported from Anki.

**Grades are stored as numbers 1–4,** the same scale as Anki. What each number means, and which
buttons the app shows, is configuration rather than database structure.

**`review_states.due_at` is `NULL` for new cards.** Creating a card is not the same as learning it:
a card only gets a due time after it is first studied.

## Conventions

- **Unicode text:** all text columns are `NVARCHAR`, so accents, Cyrillic, Devanagari and Arabic
  script are stored correctly.
- **UTC timestamps:** all times are `DATETIME2` in UTC. The `UTCDateTime` column type converts on
  the way in and out and rejects datetimes without a time zone.
- **Named constraints:** a naming convention gives every key, index and constraint a predictable
  name (e.g. `fk_cards_note_id_notes`), so migrations can refer to them.
- **Rules in the database:** `NOT NULL`, `CHECK` (grade, priority, kind, status, JSON), `UNIQUE`
  and foreign keys are enforced by SQL Server, not only by Python code.
- **Indexes** exist on the foreign keys and on `review_states.due_at`.

## Databases

| Database | Use |
| --- | --- |
| `RecallEngine` | Development data |
| `RecallEngine_test` | Automated tests; rebuilt from the migrations on every test run |

## Backups

[`backend/scripts/backup-database.ps1`](../backend/scripts/backup-database.ps1) makes a full,
checksum-verified backup of the database and keeps the newest 14 copies (by default in
`%USERPROFILE%\RecallEngine-backups`, outside the repository). It runs at most once per day, so it
can be scheduled at every Windows login with Task Scheduler. SQL Server Express has no built-in
job scheduler (SQL Agent), which is why Windows schedules it.

To restore, use SSMS: right-click **Databases → Restore Database…**, choose **Device**, and select a
`.bak` file. Restoring under a different database name is a safe way to inspect an old backup.

## Changing the schema

1. Back up the database.
2. Edit the models in `backend/app/models/`.
3. `alembic revision --autogenerate -m "describe the change"` writes a migration file.
4. Read the generated file and fix it. Autogenerate treats a renamed column as a dropped and a new
   column, cannot move data, and does not notice changed `CHECK` constraints.
5. `alembic upgrade head` applies it; `alembic downgrade -1` undoes it. Commit the model change and
   the migration together.

Prefer additive changes (new tables, new nullable columns). For renames and type changes, add the
new column, copy the data, switch the code, and remove the old column in a later migration.
A test (`tests/test_migrations.py`) fails if the models and the migrations disagree.

Never change tables by hand in SSMS: the migrations would no longer match the database.

## Not yet implemented

- Media files (images, audio): references are stored, the files are not yet.
- `CardLink` (relationships between cards), planned for Phase 2.

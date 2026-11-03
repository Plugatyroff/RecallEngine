# Recall Engine

An adaptive spaced-repetition app for remembering what you learn over the long term.

Recall Engine combines Anki-style flashcards, Obsidian-style hierarchical and linked notes, and a scheduler
that brings material back on its own. It starts with reviews only hours after first learning something,
then spaces them out as the memory becomes stable.

> **Status:** early development. The project structure is in place; the features below are planned, not yet implemented.

## Planned features

- Unlimited nested topics (e.g. Mathematics → Linear Algebra → Matrices)
- Flashcards with Markdown and LaTeX, linked to related cards
- Configurable scheduling with short initial intervals (≈2 h, 6 h, 12 h, then days)
- Mixed review sessions that balance subjects
- Android notifications for due reviews

## Tech stack

| Part     | Technology                                   |
| -------- | -------------------------------------------- |
| Frontend | React Native, Expo, Expo Router, TypeScript  |
| Backend  | Python, FastAPI, SQLAlchemy, Alembic         |
| Database | PostgreSQL                                   |

## Repository layout

```text
frontend/   Expo app (Android, web)
backend/    FastAPI REST API (planned)
docs/       Architecture and design notes (planned)
```

## Running the frontend

Requires Node.js.

```bash
cd frontend
npm install
npx expo start
```

Then scan the QR code with Expo Go on Android, or press `w` to open it in the browser.

## Project documents

- [PROJECT.md](PROJECT.md) — full product and technical specification

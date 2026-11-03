# Recall Engine

An adaptive spaced-repetition app for remembering what you learn over the long term.

Recall Engine combines Anki-style flashcards, Obsidian-style hierarchical and linked notes, and a scheduler
that brings material back on its own. It starts with reviews only hours after first learning something,
then spaces them out as the memory becomes stable.

> **Status:** early development. The basic loop works: create topics and cards, review them, see when each is due next.

## Features

Implemented:

- Unlimited nested topics (e.g. Mathematics → Linear Algebra → Matrices)
- Anki-compatible notes, note types and card templates (e.g. one note → forward and reverse card)
- Pluggable scheduling: FSRS (Anki's algorithm) by default, or fixed custom intervals such as 2 h → 6 h → 12 h → 1 d
- Review screen with Again / Hard / Good / Easy, showing when each choice brings the card back
- Review everything, a single topic with its subtopics, or a single card
- Importing Anki collections, including review history (replayed through the scheduler)

Planned:

- LaTeX rendering and media (images, audio)
- Mixed review sessions that balance subjects and bring back neglected topics
- Links between cards
- Android notifications for due reviews

## Tech stack

| Part     | Technology                                   |
| -------- | -------------------------------------------- |
| Frontend | React Native, Expo, Expo Router, TypeScript  |
| Backend  | Python, FastAPI, SQLAlchemy, Alembic         |
| Database | Microsoft SQL Server                         |

## Repository layout

```text
frontend/   Expo app (Android, web)
backend/    FastAPI REST API
docs/       Design notes, e.g. the database design
```

## Running the frontend

Requires Node.js, and the backend running (see below).

```bash
cd frontend
npm install
npx expo start
```

Then scan the QR code with Expo Go on Android, or press `w` to open it in the browser.

The app finds the backend on port 8000 of the computer running `npx expo start`. To use another
address, create `frontend/.env.local` with e.g. `EXPO_PUBLIC_API_URL=http://192.168.0.10:8000`.

## Running the backend

Requires Python 3.12+, SQL Server (Express is fine) and
[ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).

1. Create two empty databases, `RecallEngine` and `RecallEngine_test`, e.g. in SSMS.
2. Copy `backend/.env.example` to `backend/.env` and set `DB_SERVER` to your SQL Server instance.
   The backend logs in with your Windows account.
3. From the `backend` folder (commands for Windows PowerShell):

```powershell
python -m venv .venv                     # create an isolated Python environment
.venv\Scripts\Activate.ps1               # use it in this terminal
pip install -e . --group dev             # install the API and its dev tools
alembic upgrade head                     # create the tables
python scripts/seed.py                   # optional: fill in example data
pytest                                   # run the tests (uses RecallEngine_test)
uvicorn app.main:app --host 0.0.0.0 --reload
```

The API is then available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.
`--host 0.0.0.0` makes it reachable from a phone on the same Wi-Fi via the computer's local IP address.

## Importing from Anki

In Anki: **File → Export…**, choose *Anki Collection Package (.colpkg)* or *Anki Deck Package (.apkg)*,
tick **Include scheduling information** and **Support older Anki versions**. Then, from `backend`:

```powershell
python scripts/import_anki.py C:\path\to\export.colpkg --dry-run   # report only, saves nothing
python scripts/import_anki.py C:\path\to\export.colpkg             # import
```

Decks become topics, and the review history sets each card's schedule. Importing the same file
again updates the earlier import instead of duplicating it. Media files and Cloze note types are
not supported yet; media references in cards are kept.

## Project documents

- [PROJECT.md](PROJECT.md) — full product and technical specification
- [docs/database-design.md](docs/database-design.md) — tables and the reasoning behind them
- [docs/scheduling.md](docs/scheduling.md) — how reviews are scheduled and how to plug in another algorithm

## License

[MIT](LICENSE)

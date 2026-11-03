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
| Database | Microsoft SQL Server                         |

## Repository layout

```text
frontend/   Expo app (Android, web)
backend/    FastAPI REST API
docs/       Design notes, e.g. the database design
```

## Running the frontend

Requires Node.js.

```bash
cd frontend
npm install
npx expo start
```

Then scan the QR code with Expo Go on Android, or press `w` to open it in the browser.

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

## Project documents

- [PROJECT.md](PROJECT.md) — full product and technical specification
- [docs/database-design.md](docs/database-design.md) — tables and the reasoning behind them
- [docs/scheduling.md](docs/scheduling.md) — how reviews are scheduled and how to plug in another algorithm

## License

[MIT](LICENSE)

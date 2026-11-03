"""Entry point of the Recall Engine API.

Run locally with:  uvicorn app.main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Recall Engine API")

# Allow the Expo web version (served from localhost:8081 during development) to call the API.
# The phone app is not a browser, so it does not need this.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
# Files used by the app's card view, e.g. KaTeX for math (see static/README.md)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the API is running. Used to check the server is reachable."""
    return {"status": "ok"}

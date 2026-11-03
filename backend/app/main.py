"""Entry point of the Recall Engine API.

Run locally with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI

app = FastAPI(title="Recall Engine API")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the API is running. Used to check the server is reachable."""
    return {"status": "ok"}

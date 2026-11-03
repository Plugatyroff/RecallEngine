"""Memory schedulers: decide when each card should ideally be reviewed again.

Use get_scheduler() rather than importing a scheduler class directly, so the choice of
algorithm stays in config.py.
"""

from functools import cache

from app.services.scheduling.base import (
    AGAIN,
    EASY,
    GOOD,
    GRADES,
    HARD,
    CardMemory,
    MemoryScheduler,
    replay,
)
from app.services.scheduling.config import DEFAULT_SCHEDULER, SCHEDULERS


@cache
def get_scheduler(name: str = DEFAULT_SCHEDULER) -> MemoryScheduler:
    """Return the scheduler registered under this name (built once, then reused)."""
    if name not in SCHEDULERS:
        raise KeyError(f"Unknown scheduler {name!r}; registered: {sorted(SCHEDULERS)}")
    scheduler = SCHEDULERS[name]()
    if scheduler.name != name:
        raise ValueError(f"Scheduler registered as {name!r} calls itself {scheduler.name!r}")
    return scheduler


__all__ = [
    "AGAIN",
    "EASY",
    "GOOD",
    "GRADES",
    "HARD",
    "CardMemory",
    "MemoryScheduler",
    "get_scheduler",
    "replay",
]

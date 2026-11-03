"""Which schedulers exist, their settings, and which one new cards use.

To add a scheduler: write a class with `name`, `review()` and `recall_probability()`
(see base.MemoryScheduler) and register it below. To change the default, change
DEFAULT_SCHEDULER. Cards keep the scheduler they were created with; switching existing cards
means replaying their review history (base.replay).
"""

from collections.abc import Callable
from datetime import timedelta

from app.services.scheduling.base import MemoryScheduler
from app.services.scheduling.fixed_steps import FixedStepsScheduler
from app.services.scheduling.fsrs_scheduler import FsrsScheduler

MINUTE, HOUR, DAY = timedelta(minutes=1), timedelta(hours=1), timedelta(days=1)

DEFAULT_SCHEDULER = "fsrs"

# Each entry builds a scheduler; the key must equal the scheduler's name.
SCHEDULERS: dict[str, Callable[[], MemoryScheduler]] = {
    # Anki's algorithm. A failed card comes back after 10 minutes, then FSRS takes over.
    "fsrs": lambda: FsrsScheduler(
        "fsrs",
        desired_retention=0.9,
        learning_steps=[10 * MINUTE],
        relearning_steps=[10 * MINUTE],
    ),
    # The original Recall Engine hypothesis: hour-scale reviews in the first day
    "hours": lambda: FixedStepsScheduler("hours", [2 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 3 * DAY, 7 * DAY]),
    # A conventional day-scale baseline
    "days": lambda: FixedStepsScheduler("days", [DAY, 3 * DAY, 7 * DAY]),
}

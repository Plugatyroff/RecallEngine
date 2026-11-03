"""A scheduler that follows a fixed list of intervals, e.g. 2h, 6h, 12h, 1d, 3d, 7d.

Rules (intervals always count from the actual review time, so late or early reviews are fine):
- Good: move to the next step.
- Easy: skip one step.
- Hard: repeat the current step's interval.
- Again: show the card again after `retry_delay`, and go back one step, so the next success
  repeats the interval that was just failed.
After the last step, each further interval is the previous one multiplied by `growth`.
"""

import math
from collections.abc import Sequence
from datetime import datetime, timedelta

from app.services.scheduling.base import AGAIN, EASY, GOOD, HARD, CardMemory, after_review, check_review

# The recall probability this scheduler assumes when a card comes due (same target as FSRS)
_RECALL_WHEN_DUE = 0.9


class FixedStepsScheduler:
    def __init__(
        self,
        name: str,
        steps: Sequence[timedelta],
        *,
        growth: float = 2.0,
        retry_delay: timedelta = timedelta(minutes=10),
        maximum_interval: timedelta = timedelta(days=365),
    ) -> None:
        if not steps:
            raise ValueError("steps must not be empty")
        self.name = name
        self.steps = tuple(steps)
        self.growth = growth
        self.retry_delay = retry_delay
        self.maximum_interval = maximum_interval

    def interval(self, step: int) -> timedelta:
        """The interval for a step number (0 = first interval)."""
        if step < len(self.steps):
            interval = self.steps[step]
        else:
            interval = self.steps[-1] * self.growth ** (step - len(self.steps) + 1)
        return min(interval, self.maximum_interval)

    def review(self, memory: CardMemory, grade: int, reviewed_at: datetime) -> CardMemory:
        check_review(grade, reviewed_at)
        # The step whose interval was last scheduled; -1 before the first success
        step = memory.state.get("step", -1)

        if grade == AGAIN:
            step = max(step - 1, -1)
            interval = self.retry_delay
        elif grade == HARD:
            step = max(step, 0)
            interval = self.interval(step)
        else:
            step += 1 if grade == GOOD else 2
            interval = self.interval(step)

        if grade != AGAIN and interval >= timedelta(days=1):
            status = "review"
        elif memory.status in ("review", "relearning"):
            status = "relearning"
        else:
            status = "learning"

        return after_review(memory, grade, reviewed_at, status=status, interval=interval,
                            state={"step": step})

    def recall_probability(self, memory: CardMemory, at: datetime) -> float | None:
        """A rough estimate: recall falls exponentially, reaching 90% when the card is due."""
        if memory.due_at is None or memory.last_reviewed_at is None:
            return None
        scheduled = (memory.due_at - memory.last_reviewed_at).total_seconds()
        elapsed = max((at - memory.last_reviewed_at).total_seconds(), 0)
        return math.pow(_RECALL_WHEN_DUE, elapsed / scheduled)

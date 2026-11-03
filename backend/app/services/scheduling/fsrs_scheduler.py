"""FSRS (Free Spaced Repetition Scheduler), the algorithm used by Anki, via the `fsrs` package.

FSRS models each card's memory with a stability (days until recall probability falls to 90%)
and a difficulty, and schedules the next review for when recall probability is about to drop
below the desired retention. This is the only module that imports the `fsrs` package.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

import fsrs

from app.services.scheduling.base import CardMemory, after_review, check_review

_STATUSES = {
    fsrs.State.Learning: "learning",
    fsrs.State.Review: "review",
    fsrs.State.Relearning: "relearning",
}


class FsrsScheduler:
    def __init__(
        self,
        name: str = "fsrs",
        *,
        desired_retention: float = 0.9,
        learning_steps: Sequence[timedelta] = (timedelta(minutes=10),),
        relearning_steps: Sequence[timedelta] = (timedelta(minutes=10),),
        maximum_interval_days: int = 36500,
        enable_fuzzing: bool = True,
    ) -> None:
        """
        desired_retention: target chance of remembering a card when it comes due.
        learning_steps / relearning_steps: fixed short steps for new / just-forgotten cards
            before FSRS takes over. Answering Good on the last step hands the card to FSRS.
        enable_fuzzing: randomize long intervals slightly, so cards learned together do not
            all come due on the same day.
        """
        self.name = name
        self._fsrs = fsrs.Scheduler(
            desired_retention=desired_retention,
            learning_steps=tuple(learning_steps),
            relearning_steps=tuple(relearning_steps),
            maximum_interval=maximum_interval_days,
            enable_fuzzing=enable_fuzzing,
        )

    def review(self, memory: CardMemory, grade: int, reviewed_at: datetime) -> CardMemory:
        check_review(grade, reviewed_at)
        card, _ = self._fsrs.review_card(self._to_fsrs(memory), fsrs.Rating(grade), reviewed_at)
        return after_review(
            memory,
            grade,
            reviewed_at,
            status=_STATUSES[card.state],
            interval=card.due - reviewed_at,
            state={
                "fsrs_state": int(card.state),
                "step": card.step,
                "stability": card.stability,
                "difficulty": card.difficulty,
            },
        )

    def recall_probability(self, memory: CardMemory, at: datetime) -> float | None:
        if memory.status == "new" or memory.last_reviewed_at is None:
            return None
        return self._fsrs.get_card_retrievability(self._to_fsrs(memory), at)

    @staticmethod
    def _to_fsrs(memory: CardMemory) -> fsrs.Card:
        # card_id is irrelevant here; passing it avoids the 1 ms pause fsrs.Card adds otherwise
        if memory.status == "new":
            return fsrs.Card(card_id=0)
        return fsrs.Card(
            card_id=0,
            state=fsrs.State(memory.state["fsrs_state"]),
            step=memory.state["step"],
            stability=memory.state["stability"],
            difficulty=memory.state["difficulty"],
            due=memory.due_at,
            last_review=memory.last_reviewed_at,
        )

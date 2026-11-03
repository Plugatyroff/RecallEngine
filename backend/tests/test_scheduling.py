"""Tests for the memory schedulers. These need no database."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.services.scheduling import (
    AGAIN,
    EASY,
    GOOD,
    HARD,
    CardMemory,
    MemoryScheduler,
    get_scheduler,
    replay,
)
from app.services.scheduling.config import DEFAULT_SCHEDULER, SCHEDULERS
from app.services.scheduling.fixed_steps import FixedStepsScheduler
from app.services.scheduling.fsrs_scheduler import FsrsScheduler

START = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
MINUTE, HOUR, DAY = timedelta(minutes=1), timedelta(hours=1), timedelta(days=1)


def review_on_time(scheduler: MemoryScheduler, grades: list[int], start: datetime = START) -> list[CardMemory]:
    """Review a new card with these grades, each exactly when it is due. Returns every state."""
    memory, now, history = CardMemory(), start, []
    for grade in grades:
        memory = scheduler.review(memory, grade, now)
        history.append(memory)
        now = memory.due_at
    return history


def interval(memory: CardMemory) -> timedelta:
    return memory.due_at - memory.last_reviewed_at


# --- rules every scheduler must follow ------------------------------------------------------
# Any scheduler added to config.SCHEDULERS is automatically checked against these.

@pytest.fixture(params=sorted(SCHEDULERS))
def scheduler(request) -> MemoryScheduler:
    return get_scheduler(request.param)


def test_scheduler_implements_the_interface(scheduler: MemoryScheduler) -> None:
    assert isinstance(scheduler, MemoryScheduler)


def test_reviewing_a_new_card_schedules_it(scheduler: MemoryScheduler) -> None:
    memory = scheduler.review(CardMemory(), GOOD, START)

    assert memory.status != "new"
    assert memory.due_at > START
    assert memory.last_reviewed_at == START
    assert memory.review_count == 1


@pytest.mark.parametrize("history", [[GOOD], [GOOD, GOOD, GOOD], [GOOD, AGAIN, GOOD]])
def test_forgetting_never_gives_a_longer_interval_than_remembering(
    scheduler: MemoryScheduler, history: list[int]
) -> None:
    memory = review_on_time(scheduler, history)[-1]

    after_again = scheduler.review(memory, AGAIN, memory.due_at)
    after_good = scheduler.review(memory, GOOD, memory.due_at)

    assert interval(after_again) < interval(after_good)


def test_remembering_on_time_lengthens_intervals(scheduler: MemoryScheduler) -> None:
    intervals = [interval(m) for m in review_on_time(scheduler, [GOOD] * 6)[1:]]

    assert intervals == sorted(intervals)
    assert intervals[-1] > intervals[0]


def test_intervals_count_from_the_actual_review_time(scheduler: MemoryScheduler) -> None:
    memory = scheduler.review(CardMemory(), GOOD, START)
    late = memory.due_at + 3 * HOUR

    after = scheduler.review(memory, GOOD, late)

    assert after.last_reviewed_at == late
    assert after.due_at > late


def test_scheduler_state_survives_a_json_round_trip(scheduler: MemoryScheduler) -> None:
    memory = review_on_time(scheduler, [GOOD, AGAIN, GOOD])[-1]
    stored = CardMemory(**{**memory.__dict__, "state": json.loads(json.dumps(memory.state))})

    assert scheduler.review(stored, GOOD, memory.due_at) == scheduler.review(memory, GOOD, memory.due_at)


def test_recall_probability_is_unknown_for_new_cards_and_falls_over_time(scheduler: MemoryScheduler) -> None:
    assert scheduler.recall_probability(CardMemory(), START) is None

    memory = review_on_time(scheduler, [GOOD, GOOD])[-1]
    soon = scheduler.recall_probability(memory, memory.last_reviewed_at + HOUR)
    later = scheduler.recall_probability(memory, memory.due_at + 10 * DAY)
    assert 0 <= later < soon <= 1


@pytest.mark.parametrize("grade", [0, 5, "good"])
def test_invalid_grades_are_rejected(scheduler: MemoryScheduler, grade) -> None:
    with pytest.raises(ValueError):
        scheduler.review(CardMemory(), grade, START)


def test_review_time_must_have_a_time_zone(scheduler: MemoryScheduler) -> None:
    with pytest.raises(ValueError):
        scheduler.review(CardMemory(), GOOD, datetime(2026, 11, 4, 9, 0))


def test_lapses_count_cards_forgotten_after_learning(scheduler: MemoryScheduler) -> None:
    learned = review_on_time(scheduler, [GOOD] * 5)[-1]
    assert learned.status == "review"

    forgotten = scheduler.review(learned, AGAIN, learned.due_at)

    assert forgotten.lapse_count == learned.lapse_count + 1
    assert forgotten.status == "relearning"


# --- registry -------------------------------------------------------------------------------

def test_default_scheduler_is_fsrs() -> None:
    assert DEFAULT_SCHEDULER == "fsrs"
    assert isinstance(get_scheduler(), FsrsScheduler)


def test_unknown_scheduler_name_is_rejected() -> None:
    with pytest.raises(KeyError):
        get_scheduler("sm2")


def test_replay_rebuilds_memory_from_history() -> None:
    scheduler = get_scheduler("hours")
    history = review_on_time(scheduler, [GOOD, GOOD, AGAIN, GOOD])
    reviews = [(GOOD, START), (GOOD, history[0].due_at), (AGAIN, history[1].due_at), (GOOD, history[2].due_at)]

    assert replay(scheduler, reviews) == history[-1]


# --- fixed steps ----------------------------------------------------------------------------

STEPS = [2 * HOUR, 6 * HOUR, 12 * HOUR, DAY, 3 * DAY, 7 * DAY]


def fixed() -> FixedStepsScheduler:
    return FixedStepsScheduler("test", STEPS, growth=2.0, retry_delay=10 * MINUTE)


def test_fixed_steps_follow_the_custom_intervals_then_grow() -> None:
    intervals = [interval(m) for m in review_on_time(fixed(), [GOOD] * 8)]

    assert intervals == STEPS + [14 * DAY, 28 * DAY]


def test_fixed_steps_status_changes_to_review_at_one_day() -> None:
    statuses = [m.status for m in review_on_time(fixed(), [GOOD] * 4)]

    assert statuses == ["learning", "learning", "learning", "review"]


def test_fixed_steps_again_retries_soon_and_goes_back_one_step() -> None:
    at_12h = review_on_time(fixed(), [GOOD] * 3)[-1]  # last interval: 12 h

    failed = fixed().review(at_12h, AGAIN, at_12h.due_at)
    retried = fixed().review(failed, GOOD, failed.due_at)

    assert interval(failed) == 10 * MINUTE
    assert interval(retried) == 12 * HOUR  # repeats the interval that was failed


def test_fixed_steps_hard_repeats_and_easy_skips_a_step() -> None:
    at_6h = review_on_time(fixed(), [GOOD] * 2)[-1]  # last interval: 6 h

    assert interval(fixed().review(at_6h, HARD, at_6h.due_at)) == 6 * HOUR
    assert interval(fixed().review(at_6h, EASY, at_6h.due_at)) == DAY


def test_fixed_steps_respect_the_maximum_interval() -> None:
    scheduler = FixedStepsScheduler("test", [DAY], growth=10.0, maximum_interval=30 * DAY)

    assert interval(review_on_time(scheduler, [GOOD] * 4)[-1]) == 30 * DAY


# --- FSRS -----------------------------------------------------------------------------------

def fsrs_scheduler() -> FsrsScheduler:
    return FsrsScheduler(enable_fuzzing=False)  # deterministic intervals for tests


def test_fsrs_new_card_failed_comes_back_after_the_learning_step() -> None:
    memory = fsrs_scheduler().review(CardMemory(), AGAIN, START)

    assert memory.status == "learning"
    assert interval(memory) == 10 * MINUTE


def test_fsrs_new_card_remembered_goes_to_long_term_review() -> None:
    memory = fsrs_scheduler().review(CardMemory(), GOOD, START)

    assert memory.status == "review"
    assert interval(memory) >= DAY
    assert memory.state["stability"] > 0


def test_fsrs_late_but_remembered_review_gives_a_longer_interval() -> None:
    memory = fsrs_scheduler().review(CardMemory(), GOOD, START)

    on_time = fsrs_scheduler().review(memory, GOOD, memory.due_at)
    late = fsrs_scheduler().review(memory, GOOD, memory.due_at + 3 * DAY)

    assert interval(late) > interval(on_time)


def test_fsrs_recall_probability_is_about_the_target_when_due() -> None:
    memory = review_on_time(fsrs_scheduler(), [GOOD, GOOD])[-1]

    assert fsrs_scheduler().recall_probability(memory, memory.due_at) == pytest.approx(0.9, abs=0.02)

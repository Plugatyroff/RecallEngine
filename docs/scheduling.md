# Scheduling

Deciding what to review and when is split into three independent, replaceable parts:

```text
 grade, time  →  1. Memory scheduler      →  ideal next due time for each card
                 2. Notification planner  →  when to notify (merges nearby due times, quiet hours)
 app opened   →  3. Session builder       →  which cards to review now, in what order
```

Each part only receives inputs and returns a decision, so any one of them can be replaced
without changing the others. Only the memory scheduler is implemented so far.

## Memory schedulers

Code: [`backend/app/services/scheduling/`](../backend/app/services/scheduling/).

A memory scheduler is any class with:

| Member | Purpose |
| --- | --- |
| `name` | Stored with each card (`review_states.scheduler`), so a card is always rescheduled by the scheduler that owns it |
| `review(memory, grade, reviewed_at)` | Returns the card's memory after a review, counting from the actual review time |
| `recall_probability(memory, at)` | Estimated chance of remembering the card at a given time, or `None` if unknown; used later to prioritise at-risk cards |

`CardMemory` holds the fields every scheduler provides (`status`, `due_at`, `last_reviewed_at`,
`review_count`, `lapse_count`) plus a private `state` dictionary, stored as JSON in
`review_states.scheduler_state`. Nothing outside a scheduler reads that private state.

Grades are 1–4 (Again, Hard, Good, Easy), as in Anki.

### Available schedulers

Registered in [`config.py`](../backend/app/services/scheduling/config.py):

| Name | Behaviour |
| --- | --- |
| `fsrs` (default) | FSRS, Anki's algorithm, via the [`fsrs`](https://github.com/open-spaced-repetition/py-fsrs) package. Targets 90% recall when a card comes due. A failed card returns after 10 minutes, then FSRS schedules it. |
| `hours` | Fixed steps 2 h → 6 h → 12 h → 1 d → 3 d → 7 d, then doubling. |
| `days` | Fixed steps 1 d → 3 d → 7 d, then doubling. |

Fixed-step rules: Good moves to the next step, Easy skips one, Hard repeats the current interval,
Again brings the card back after 10 minutes and goes back one step.

FSRS's default model treats several reviews on the same day as adding almost no long-term
memory strength, so the hour-scale steps of `hours` mainly add review effort. Whether that holds
for the user's own memory is an open question that the `hours` and `days` schedulers allow testing.

### Adding or changing a scheduler

1. Write a class with `name`, `review()` and `recall_probability()` (see `base.MemoryScheduler`).
2. Register it in `config.SCHEDULERS`; change `DEFAULT_SCHEDULER` to make new cards use it.
3. The tests in `tests/test_scheduling.py` run their general rules against every registered
   scheduler automatically (e.g. forgetting never gives a longer interval than remembering).

Existing cards keep their scheduler. To move them to another one, replay their review history
(`replay()`), which works because every review is kept in the `reviews` table.

### Recording a review

`app.services.reviews.record_review()` loads a card's memory, asks the card's scheduler for the
new memory, stores it in `review_states`, and appends the review (grade, answer time, resulting
due time, scheduler name) to `reviews`.

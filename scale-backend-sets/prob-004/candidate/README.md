# Annotation task service

Our annotation platform hands labelling tasks ("is this review positive?",
"what vehicle is in this frame?") to a pool of human annotators. This service
is already in production: it stores tasks in SQLite, lets annotators pick up
work and records their answers. It has problems, and you will fix and extend
it in three parts. Your interviewer gives you `PART1.md` first; the next part
comes when you finish.

**Read the existing code before you change it.** It is small (about 270 lines).

## Layout

```
app/main.py            create_app(): routes (start here)
app/db.py              TaskStore: SQLite schema and queries (storage_dir/tasks.db)
app/models.py          pydantic request models and batch-entry validation
mock_services/clock.py RealClock / FakeClock (tests control time with FakeClock)
data/tasks_seed.json   a sample batch, including entries the API must reject
scripts/seed.py        posts the sample batch to a running server
tests/                 tests for the existing endpoints; add yours here
```

## Setup

Python 3.10+ with `fastapi uvicorn httpx pydantic pytest`.

```
python -m pytest                                         # run tests
uvicorn --factory app.main:create_app --port 8000        # data goes to ./storage/tasks.db
python scripts/seed.py
```

## The API today

Annotators identify themselves with the `X-Annotator-Id` header.

| endpoint | behaviour |
|---|---|
| `POST /tasks` | Body `{"tasks": [{"id"?, "data": {...}, "labels": [...]}]}`. Each entry is validated on its own: `id` (optional, generated if missing) matches `^[A-Za-z0-9_-]{1,64}$` and is not already used; `data` is an object; `labels` is a non-empty list of distinct non-empty strings. Unknown keys are ignored. **201** `{"created": [ids in batch order], "errors": [{"index", "error"}]}`. |
| `GET /tasks/{id}` | **200** the task, **404** if unknown. |
| `GET /tasks?state=` | **200** `{"tasks": [...]}` in creation order, optionally filtered by state. |
| `POST /tasks/claim` | Returns the oldest pending task, or **204** if there is none. |
| `POST /tasks/{id}/submit` | Body `{"label": "..."}`. Records the label and marks the task `submitted`. |
| `GET /health` | `{"status": "ok", "time": <clock time>}` |

A task looks like:

```json
{"id": "rev-001", "data": {"text": "..."}, "labels": ["positive", "negative", "neutral"],
 "state": "pending", "created_at": 1700000000.0,
 "submissions": [{"annotator_id": "alice", "label": "positive", "submitted_at": 1700000012.0}]}
```

```
curl -s localhost:8000/tasks -H 'content-type: application/json' \
     -d '{"tasks": [{"id": "t1", "data": {"text": "hi"}, "labels": ["a", "b"]}]}'
curl -s -X POST localhost:8000/tasks/claim -H 'X-Annotator-Id: alice'
curl -s localhost:8000/tasks/t1/submit -H 'X-Annotator-Id: alice' \
     -H 'content-type: application/json' -d '{"label": "a"}'
curl -s 'localhost:8000/tasks?state=pending'
```

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.

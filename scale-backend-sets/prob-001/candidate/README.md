# Ticket triage service

Our support team receives ticket exports from many customers and wants them
triaged automatically. You will build the service in three parts. Your
interviewer gives you `PART1.md` first; the next part comes when you finish.

## Layout

```
app/main.py           create_app(): the FastAPI app (start here)
mock_services/llm.py  make_llm(): the in-process mock LLM you will call in Part 2
mock_services/clock.py RealClock / FakeClock
data/                 sample files, including broken rows
tests/                put your tests here
```

## Setup

Python 3.10+ with `fastapi uvicorn httpx pydantic pytest python-multipart`.

```
python -m pytest              # run tests
uvicorn app.main:app --reload # run the service on :8000
curl -F file=@data/tickets.csv localhost:8000/uploads
```

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.

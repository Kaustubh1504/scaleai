# Resilient task exporter

A customer wants a nightly export of their projects' tasks as files they can
load into their warehouse. The data comes from our **Tasks API**, which is
flaky and strictly rate limited. You will build the exporter in three parts;
your interviewer gives you `PART1.md` first.

## Layout

```
API.md                  the API documentation (start here)
exporter/client.py      TasksClient: talks to the API (you write this)
exporter/export.py      Exporter: writes the files (you write this)
exporter/__main__.py    CLI wrapper, already done: python -m exporter --project prj_01 --out exports/
mock_services/api.py    make_api(): the API running in-process, for tests
mock_services/clock.py  RealClock / FakeClock
data/recorded/          example raw responses (429, 503, truncated body, ...)
tests/                  put your tests here
```

## Setup

Python 3.10+ with `httpx pytest` (and `fastapi uvicorn` to run the mock as a server).

```
python -m pytest
python -m mock_services.api_server --port 9300 &     # optional: the API over real HTTP
python -m exporter --project prj_01 --project prj_02 --out exports/
```

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.

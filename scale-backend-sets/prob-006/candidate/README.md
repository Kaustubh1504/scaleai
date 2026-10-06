# Project throughput report

Operations tracks customer annotation projects in a third-party **Projects API**.
You will write a client for it and a nightly report, in three parts. Your
interviewer gives you `PART1.md` first; the next part comes when you finish.

## Layout

```
API.md                  the API documentation (start here)
report/client.py        ApiClient: talks to the API (you write this)
report/report.py        build_report(): computes the report (you write this)
report/__main__.py      CLI wrapper, already done: python -m report --out report.json
mock_services/api.py    make_api(): the API running in-process, for tests
mock_services/clock.py  RealClock / FakeClock
data/recorded/          example raw responses
tests/                  put your tests here
```

## Setup

Python 3.10+ with `httpx pytest` (and `fastapi uvicorn` to run the mock as a server).

```
python -m pytest
python -m mock_services.api_server --port 9300 &      # optional: the API over real HTTP
python -m report --base-url http://127.0.0.1:9300 --out report.json
```

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.

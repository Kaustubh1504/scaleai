# Annotator earnings

Contributors on our annotation platform are paid per approved submission. Every
pay period, finance runs `earnings/` to work out what each annotator is owed
from the **Contributor Platform API** (`API.md`): submissions are joined to
their task (for the reward), their reviews (for the verdict) and the annotator
(for the account status).

An intern wrote `earnings/` last quarter. Finance has since found that it
underpays people. You will fix and extend it in three parts. Your interviewer
gives you `PART1.md` first; the next part comes when you finish.

**Read the existing code before you change it.** It is small (about 200 lines).

## Layout

```
API.md                     the API documentation
earnings/client.py         EarningsClient: auth + requests to the API
earnings/calc.py           compute_earnings(): the pay-period calculation
earnings/cli.py            python -m earnings ... writes a CSV
mock_services/api.py       make_api(): the API running in-process, for tests
mock_services/api_server.py  the same API over real HTTP
mock_services/clock.py     RealClock / FakeClock
data/recorded/             real example responses from the API
tests/                     the intern's tests; add yours here
```

## Setup

Python 3.10+ with `httpx pytest` (and `fastapi uvicorn` to run the mock as a server).

```
python -m pytest
python -m mock_services.api_server --port 9300 &        # the API over real HTTP (add --clean for canonical data)
python -m earnings --base-url http://127.0.0.1:9300 --start 2024-04-01 --end 2024-04-15 --out earnings.csv
```

Credentials for the mock: `client_id=finance`, `client_secret=finance-secret`.

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.

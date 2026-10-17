# Scratch sets: build from zero, timed

No starter code. Each problem folder has only:

```
SPEC.md     the problem (open it when you start the timer)
data/       input files, where the problem needs them
app/ lb/    empty folders: your code goes here (and tests/ for your tests)
_grader/    hidden acceptance tests + a reference solution. DON'T OPEN until you're done.
```

| # | Problem | Time | You write |
|---|---|---|---|
| 01 | CSV → JSON + OpenAI classification (paths, retries, concurrency, checkpoint) | 60 min | `app/main.py` (FastAPI) |
| 02 | Load balancer / task dispatcher (states, leases, retries, drain, scaling) | 75 min | `lb/balancer.py` |
| 03 | CSV upload endpoint (multipart, size/type checks, reuse 01) | 30 min | `app/main.py` |
| 04 | Single LLM-call feature (`/triage`, structured JSON, failure codes) | 30 min | `app/main.py` |
| 05 | Task processor (deadline heap, subtask deps, lazy deletion) | 30 min | `processor.py` |
| 06 | Ticket enrichment: CSV + Customer REST API (retries, per-id cache) + LLM urgency/SLA | 60 min | `app/main.py` (FastAPI) |
| 07 | Labeling pipeline (Scale-style, 3 parts; details in SPEC) | 60 min | `app/main.py` (FastAPI) |

## Setup (once)

```bash
cd scale-scratch-sets
../.venv/bin/pip install -r requirements.txt
export OPENAI_API_KEY=sk-...        # real key, for 01 / 03 / 04
```

## Grading (after the timer)

```bash
cd 01-csv-llm-pipeline
../../.venv/bin/python -m pytest _grader -q                      # everything except live tests
RUN_LIVE=1 ../../.venv/bin/python -m pytest _grader -q -m live   # real OpenAI calls (costs cents)
```

The LLM problems use your real OpenAI key. The grader's fault tests (429, 5xx, timeouts,
garbage output) point `OPENAI_BASE_URL` at a local fake OpenAI server in `_grader_shared/`,
because the real API can't be made to fail on demand. So your code **must honor
`OPENAI_BASE_URL`** (the official `openai` SDK does by default) and must do its own
retries (`max_retries=0` on the SDK).

To redo a problem: `rm -rf app/* tests/* output/` (keep the folders).

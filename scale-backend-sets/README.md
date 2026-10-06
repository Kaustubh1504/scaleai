# Scale backend-practical practice set

100 problems that mimic Scale AI's 60-minute "Backend Practical" round: Python,
open book (no AI assistants), delivered in three parts that each extend the
last, graded on execution, debugging, systematic thinking, production quality,
testing, ownership and communication.

`manifest.json` lists every problem (id, title, kind, topics, mode, difficulty, status).
At least 60% are **api-client** problems: the candidate gets a mock API
(`API.md` + `shared/mock_rest`) and must query it (auth, pagination, errors, rate
limits, messy nested JSON, joins) to compute an answer or write results. The rest
are **service** problems (build an ingestion pipeline, an LLM classifier, a load
balancer, ...). prob-001 and prob-006 are the reference examples of each kind.
Status is `planned` → `built` → `verified`; only `tools/verify_problem.py
--mark-verified` sets `verified`.

## Running an interview

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. Give the candidate the problem (PART2/PART3 are revealed later)
python tools/export_candidate.py prob-001 ~/interview --part1-only

# 2. Follow prob-001/interviewer/INTERVIEWER_NOTES.md (timeline, mid-part change, hints)

# 3. Afterwards, run the acceptance suite against their code and score with RUBRIC.md
SOLUTION_DIR=~/interview/prob-001 python -m pytest prob-001/interviewer/hidden_tests -q
```

Each problem has a 60-minute mode (all three parts) and a 30-minute mode
(Part 1 plus the start of Part 2), both described in its notes.

## Layout

```
manifest.json          index of all problems (resumable build state)
shared/                mock REST API (mock_rest), mock LLM, workers, webhook receiver, fake clock
tools/verify_problem.py  build checks: reference tests, hidden tests vs reference and starter, offline, <30 s, LOC budget
tools/manifest.py      check | table | next | sync
tools/export_candidate.py
tools/AUTHORING.md     conventions every problem follows
prob-XXX/candidate/    what the candidate gets
prob-XXX/interviewer/  notes, rubric, reference solution, hidden tests
```

## Building more problems

```bash
python tools/manifest.py next          # first problem that is not verified yet
python tools/manifest.py check         # topic-combination uniqueness and mix targets
python tools/verify_problem.py prob-006 --mark-verified
python -m pytest shared/tests          # the mock library's own tests
```

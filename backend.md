You are building a practice library of 100 backend-practical interview problems that
mimic Scale AI's "Backend Practical" round. Read this whole spec before starting.

## The real round (what we are mimicking)
- 60 minutes, Python, open book (docs, Google, StackOverflow; no AI assistants).
- Evaluated on: correctly executing the tasks, debugging and unblocking yourself,
  systematic thinking, production-quality, well-tested code, and taking the problem
  from start to finish.
- Delivered in parts, with each part extending the previous one. Reported real example:
  Part 1: a POST endpoint that accepts a data file, converts it to JSON, and saves it
  locally. Part 2: send the ingested data to an LLM for classification and persist the
  results. Another reported variant: clone a starter repo and implement a lightweight
  load balancer (worker states active/overloaded/unreachable, priority task queue,
  dynamic worker joining, heartbeats, failover).
- Follow-ups probe: LLM failures and inconsistent output, rate limiting, async
  processing, scaling to 100x.

## Output
Create `scale-backend-sets/` with `prob-001` … `prob-100` and a root `manifest.json`
(id, title, topics, mode, difficulty, status). Each problem contains:
- `candidate/`
  - `PART1.md`, `PART2.md`, `PART3.md`: the interviewer reveals each part only after
    the previous one is done. Each states requirements precisely, including error
    behavior.
  - Starter code: for ~40% of problems, an existing repo to extend (the candidate must
    read unfamiliar code first); for the rest, a minimal skeleton.
  - `data/` sample inputs, including malformed rows and edge cases.
  - `mock_services/`: local fakes for anything external (see below).
- `interviewer/`
  - `INTERVIEWER_NOTES.md`: timeline for 60-min mode and 30-min mode (30-min = Part 1
    plus the start of Part 2), when to reveal each part, the mid-part requirement
    change to drop in, a hint ladder, and 3 follow-up questions on scaling and
    failure with what a strong answer covers.
  - `reference/`: a complete production-quality solution with its own tests.
  - `hidden_tests/`: an acceptance suite to run against the candidate's final code,
    split by part.
  - `RUBRIC.md`: scores 1–4 on: correct execution, debugging and unblocking,
    systematic thinking, production quality, testing, end-to-end ownership,
    communication. Describe what a 4 and a 2 look like for THIS problem.

## Mock external services (shared library, reused across problems)
Build `scale-backend-sets/shared/` first:
- `mock_llm`: an importable client AND a runnable local HTTP server. Configurable
  latency, failure rate, timeouts, HTTP 429 rate limiting, malformed JSON, markdown-
  fenced JSON, wrong labels, inconsistent answers to the same input, and a token/cost
  counter. Deterministic via seed so tests are reproducible.
- `mock_worker`: a fake worker/node that can be killed, slowed, or go silent
  (for load balancer and scheduler problems).
- `mock_webhook_receiver` and a fake clock utility for time-based problems.

## Topics (combine 2–4 per problem; escalate across parts)
file upload and ingestion (CSV/JSONL → JSON, validation, bad-row reports, streaming
large files); LLM classification and enrichment (batching, retries with backoff and
jitter, schema validation of output, caching, cost tracking); async jobs (job ids,
status polling, worker pool, dead-letter queue); rate limiting (token bucket, sliding
window, per user/tenant); idempotency keys and dedupe; leases and timeouts for task
claiming; consensus and gold-task quality scoring for annotations; task lifecycle state
machine; load balancer with heartbeats and failover; priority and dependency-aware job
scheduling; caching proxy with TTL; leaderboard and ranking; reservation/holds without
double-booking; LLM-as-judge eval harness (repeated runs, variance, position bias);
multi-tenant isolation and quotas; pagination, filtering and sorting endpoints;
webhooks with retries; annotator fraud detection; contributor payout calculation;
audit logging.

## Part structure (every problem)
- Part 1 (~20 min): core working feature plus basic tests.
- Part 2 (~20 min): extension that adds an external dependency or new state
  (usually the mock LLM or workers), with error handling.
- Part 3 (~20 min): scale or failure hardening (concurrency, rate limits, retries,
  restarts, large input). Partly code, partly discussion.
Requirements must be unambiguous enough that the hidden tests are fair.

## Tech constraints
Python 3.10+. Allowed dependencies: fastapi, uvicorn, httpx, pydantic, pytest.
Roughly 30% of problems should be plain-Python services or CLIs (no web framework),
since the round says no advanced framework knowledge is required.
No real network calls, no databases beyond sqlite or JSON files, no Docker.

## Build process (mandatory, per problem)
1. Write the reference solution and its tests; all pass.
2. Write the hidden acceptance tests per part; they must all pass on the reference
   and fail on the untouched starter code.
3. Confirm everything runs offline in under 30 seconds with the mock services.
4. Sanity check that the reference is achievable in about 60 minutes by a strong
   candidate (lines of code per part < ~120). If not, cut scope.
5. Mark verified in the manifest only after steps 1–4 pass.
Write `tools/verify_problem.py` to automate steps 1–3.

## Workflow
- Build `shared/` first, then work in batches of 5 problems. After each batch, print a
  summary table (id, title, topics, mode, difficulty) and stop for my review.
- Resumable from `manifest.json`.
- Ramp difficulty: 1–20 medium, 21–70 hard, 71–100 very hard (multiple interacting
  failure modes, starter repos with existing tech debt).
- Problems 1–10 must include close variants of the two reported real problems
  (file ingestion + LLM classification; load balancer).
- No two problems may share the same topic combination.

## Additional coverage (required)
Add these topics to the pool:
- Third-party API consumption: cursor pagination, auth token expiry and refresh,
  honoring Retry-After on 429, partial failure across pages (extend mock services).
- Durable local persistence: atomic writes (temp file + rename), resume after crash
  without reprocessing, idempotent re-runs.
- Human-in-the-loop routing by model confidence, with a review queue and audit trail.
- Agent/tool-calling loop: model proposes tool calls, service executes them, with
  max steps, tool errors, and loop detection (add a mock tool-calling LLM mode).
- Streaming LLM responses (SSE), token counting, chunking long text to fit context.
- PII redaction before sending data to the LLM.
- Observability: request IDs, structured logging, a /metrics or /health endpoint.
- Annotation-domain services: IoU-based QA, preference-pair collection and ranking,
  SFT dataset export.

Starter-repo bugs: in ~30% of the problems that use starter repos, plant 1–2 realistic
bugs in the existing code that block Part 1 or Part 2. Document them in
INTERVIEWER_NOTES.md (the candidate must debug and unblock themselves).


Start with `shared/`, then prob-001 to prob-005.

## Format update (from a current Scale engineer)
- The candidate receives a mock API endpoint and must query it to solve a problem.
  At least 60% of problems must center on API CLIENT work: querying, paginating,
  authenticating, handling errors and rate limits, parsing nested and inconsistent
  JSON, joining data across endpoints, and computing an answer or writing results.
- Build a configurable mock REST API in shared/ with: multiple related resources,
  page/offset/cursor pagination, auth tokens that expire, 429 with Retry-After,
  random 500s, nullable and inconsistently typed fields, nested objects, and
  deterministic seeds.
- The remaining 40%: build-a-service problems (ingestion, LLM classification,
  load balancer, etc.) as before.

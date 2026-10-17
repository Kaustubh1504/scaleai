# Interviewer sheet: 07 labeling pipeline (60 min)

For the person running the mock. The candidate must not see this folder (`_grader/`).

## Before you start

* The candidate has the repo, a Python venv with `requirements.txt` installed, and their own
  `OPENAI_API_KEY`. AI assistants (Copilot, Claude, ChatGPT, editor autocomplete) are **off**.
  Docs, Google and StackOverflow are allowed. That matches the real round.
* Have them open `drills/07-labeling-pipeline/round-NN/` and start the timer when they open `SPEC.md`.
* Let them read for 3–4 minutes. Answer clarifying questions from the spec; if the spec is
  silent, tell them to pick something reasonable and say it out loud.

## Timeline and what to look for

| Clock | Part | Good signs | Nudge if stuck (say this, nothing more) |
|---|---|---|---|
| 0–20 | 1: CSV + consensus | `csv` module, not `split(",")`; `utf-8-sig`; `Path.resolve()` + `is_relative_to`; temp file + `os.replace` | "What does `../` do after you resolve it?" · "What if the process dies mid-write?" |
| 20–40 | 2: LLM | Only disputed tasks call the LLM; separate transport and validation budgets; candidates come from the votes | "How many calls happen for a 503 that never recovers?" · "Is `spam` valid for a task nobody voted spam?" |
| 40–55 | 3: callbacks | Serializes the body **once** and signs those bytes; same Idempotency-Key on retries; `asyncio.Semaphore` | "What exactly does the HMAC cover?" |
| 55–60 | Discussion | See below | |

If they're still on Part 1 at 25 minutes, tell them to move on. Partial credit across parts
beats a perfect Part 1.

### Traps in the sample data (don't reveal)

* **Exactly 2/3** (P03: 2 of 3) is *agreed*. Float comparisons like `top/total >= 0.6667` get it wrong; `3*top >= 2*total` is safe.
* ` safe ` with spaces must count as `safe` (P02).
* P05 has a duplicate annotator and an invalid label, leaving 2 votes, so it's *insufficient*.
* P07 is a multiline quoted field. The LLM first replies with an allowed but **non-candidate** label.
* P09's text is a prompt injection.
* Callbacks: signing `json.dumps(payload)` and then sending `json=payload` signs different bytes from the ones sent, so every callback gets a 401.

## Discussion: what a strong answer touches

1. **Timeout but delivered:** at-least-once delivery. The customer dedupes by Idempotency-Key; we never assume a timeout means it wasn't received.
2. **Webhook down 6h:** an outbox table (task, payload, attempts, next_attempt_at), a worker with capped exponential backoff and jitter, a dead-letter queue after N attempts, and a "redeliver" API.
3. **LLM tie-breaks:** mark them (`resolved_by`), sample them for human review, measure agreement against a gold set, and route low-confidence cases to an expert queue instead.
4. **Annotator weighting:** accuracy on gold/honeypot tasks; weighted votes; minimum trust; drift over time.
5. **Scale:** stream-parse; a job table plus a queue; idempotent workers per shard; results in object storage; progress checkpoints.

## Grading (after the timer)

```bash
cd drills/07-labeling-pipeline/round-NN
./grade.sh                    # all parts, both APIs faked
./grade.sh -k part1           # one part
RUN_LIVE=1 OPENAI_API_KEY=sk-... ./grade.sh -m live   # real OpenAI, costs a fraction of a cent
```

Rough bar: Part 1 fully green plus most of Part 2 is a pass. All three parts green, plus
their own tests, is strong. Also weigh what the tests can't see: talking through trade-offs,
debugging calmly, readable code, and tests they wrote themselves.

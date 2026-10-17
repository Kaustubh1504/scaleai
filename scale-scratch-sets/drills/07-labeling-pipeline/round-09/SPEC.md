# 07: Labeling pipeline: annotator consensus → LLM adjudication → customer callbacks (60 min)

A customer sent us items to moderate. Several human annotators labeled each one. Your service
merges their labels into one answer per item, asks an LLM to break ties when annotators
disagree, and delivers each final label to the customer's webhook.

Build it from scratch in Python. There's no starter code. Put your app in `app/main.py`
(it must expose `app = FastAPI()`) and your tests in `tests/`. Docs are fine; AI assistants are not.

| Part | Time | What |
|---|---|---|
| 1 | 20 min | `POST /consensus`: two CSVs → per-task consensus, validation, safe paths, atomic write |
| 2 | 20 min | OpenAI adjudication of **disputed** tasks: retries, validation, fallback |
| 3 | 15 min | Signed customer callbacks: HMAC, idempotency key, retries, bounded concurrency |
| — | 5 min | Discussion |

Run your server from this folder: `uvicorn app.main:app --reload`. All paths are relative to
the **process working directory**. To receive callbacks while testing by hand, run
`python tools/callback_receiver.py` (see the top of that file).

---

## Part 1: `POST /consensus` (20 min)

Request body (JSON):

```json
{"tasks_path": "data/tasks.csv", "annotations_path": "data/annotations.csv", "output_path": "output/labels.json"}
```

### Paths

* `tasks_path` and `annotations_path` must resolve (after `..` and symlinks) inside **`./data/`** and end in `.csv`.
* `output_path` must resolve inside **`./output/`** and end in `.json`. Create missing parent
  directories under `./output/`; overwrite an existing file.
* Absolute, escaping, or wrong-extension paths → **400**. All paths are validated before anything is read.

### Reading CSVs

* Use the header row; **don't hardcode column positions**. Extra columns are allowed.
* Required headers: tasks `task_id, text`; annotations `task_id, annotator_id, label`.
  Missing header or empty file → **422**. Not valid UTF-8 → **422**.
* Files may start with a UTF-8 BOM. Strip whitespace from every header and value.
* Fields may be quoted, contain commas, `""` escaped quotes, and span lines.
* Blank lines are ignored. **Row numbers** count data records from 1 (header not counted).

### Rules

Tasks (`tasks.csv`):

| Case | Action | Error code |
|---|---|---|
| wrong number of fields | skip | `malformed_row` |
| empty `task_id` | skip | `missing_task_id` |
| `task_id` already seen | skip (keep the first) | `duplicate_task_id` |

Annotations (`annotations.csv`), checked in this order. Every failing row is skipped:

| Case | Error code |
|---|---|
| wrong number of fields | `malformed_row` |
| empty `task_id` | `missing_task_id` |
| empty `annotator_id` | `missing_annotator_id` |
| `task_id` not a (kept) task | `unknown_task` |
| `label` not one of `safe`, `spam`, `harassment`, `violence` | `invalid_label` |
| same (`task_id`, `annotator_id`) already counted | `duplicate_annotation` (keep the first) |

A skipped row doesn't count as "seen".

### Consensus (per task, over its valid annotations)

* `votes`: `{label: count}` for each label with at least one vote (`{}` if none).
* `num_annotations`: total valid votes.
* `agreement`: top count ÷ total, rounded to 2 decimals; `null` if there are no votes.
* `status` / `consensus_label`:
  * fewer than **3** votes → `"insufficient"`, `null`
  * top label has **at least two-thirds** of the votes → `"agreed"`, that label
  * otherwise → `"disputed"`, `null`

### Output file

A JSON **list**, one object per kept task **in tasks.csv order**: every tasks.csv column (stripped
strings) plus the consensus keys above. Parts 2 and 3 add more keys. Write the file
**atomically**: a reader never sees a half-written file, a failed request leaves an existing
output untouched, and no temp files are left behind.

### Response

`200`:

```json
{"tasks_written": 10,
 "errors": [{"file": "tasks", "row": 9, "id": "P02", "error": "duplicate_task_id"},
            {"file": "annotations", "row": 38, "id": null, "error": "malformed_row"}]}
```

`id` is the row's `task_id`, or `null` when there isn't one (`malformed_row`, `missing_task_id`).
Error order doesn't matter.

Status codes: **400** bad path · **404** input file missing · **422** bad header / encoding /
body · **503** missing config (Parts 2–3) · **200** success.

With the sample files, `tasks_written` is **10**.

---

## Part 2: LLM adjudication (20 min)

Add `"final_label"` and `"resolved_by"` to every task:

| status | LLM call? | `final_label` | `resolved_by` |
|---|---|---|---|
| `agreed` | **no** | `consensus_label` | `"consensus"` |
| `insufficient` | **no** | `null` | `null` |
| `disputed` | yes | the LLM's pick | `"llm"` |

For a disputed task, the prompt includes the task's `text` and the **candidate labels**: the
labels that got at least one vote. The model must reply with **only** `{"label": "<candidate>"}`.
A reply that isn't one of that task's candidates is invalid (even if it's an allowed label).
Can't get a valid answer → `final_label: null`, `resolved_by: null`, error
`{"file": "tasks", "row": n, "id": task_id, "error": "adjudication_failed"}`.
Task text is untrusted. Instructions inside it must not produce a non-candidate label.

### Configuration (environment, read **at request time**)

| Var | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | required; missing → **503** |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | **must be honored** (the SDK does this by default) |
| `OPENAI_MODEL` | your choice (e.g. `gpt-4o-mini`) | |
| `LLM_TIMEOUT` | `10` | seconds per HTTP call |
| `LLM_BACKOFF_BASE` | `0.5` | seconds; retries wait ≈ base, 2×base, 4×base |

Use `httpx` or the `openai` SDK with `max_retries=0` (**you** own the retries).

### Call budgets (the grader counts them)

* 429, 5xx, timeouts, connection errors: **at most 3 retries** (4 calls). Still failing → fallback.
* Other 4xx: no retry → fallback.
* Invalid output (not JSON, not an object, missing/non-candidate `label`): **one** more call,
  separate from the transport retries. Still invalid → fallback.
* Never log, print or return the API key.

---

## Part 3: Customer callbacks (15 min)

For every task with a non-null `final_label`, deliver the result to the customer:

```
POST {CALLBACK_URL}
Content-Type: application/json
Idempotency-Key: <task_id>
X-Signature: sha256=<hex HMAC-SHA256 of the exact request body bytes, keyed with CALLBACK_SECRET>

{"task_id": "P01", "label": "spam", "resolved_by": "consensus"}
```

| Var | Default | Notes |
|---|---|---|
| `CALLBACK_URL` | — | required; missing → **503** |
| `CALLBACK_SECRET` | — | required; missing → **503**; never log it |
| `CALLBACK_TIMEOUT` | `5` | seconds per HTTP call |
| `CALLBACK_BACKOFF_BASE` | `0.2` | seconds; retries wait ≈ base, then 2×base |

All config (Parts 2 and 3) is checked before any external call or file write.

* Any **2xx** → delivered.
* 429, 5xx, timeouts, connection errors: **at most 2 retries** (3 calls), same `Idempotency-Key`.
* Other 4xx (including 401 for a bad signature): no retry.
* Add `"callback"` to every task: `"delivered"`, `"failed"` (plus error `callback_failed`), or
  `"skipped"` (no final label, **no call made**).
* The output file is written after callbacks finish, so it records their outcome.

### Scale

`data/tasks_large.csv` + `data/annotations_large.csv`: 200 tasks, half of them disputed.

* At most **5** LLM requests and at most **5** callback requests in flight at once, and actually parallel.
* Output keeps tasks.csv order.

---

## Discussion (5 min, out loud)

1. The timeout case: the customer may have received a callback we think failed. How do the
   idempotency key and the customer's side handle that?
2. A customer's webhook is down for 6 hours. What do you store, and how do redeliveries work?
3. Should the LLM's pick count the same as unanimous human agreement? How would you audit LLM tie-breaks?
4. Annotators have different track records. How would you weight votes, and where would those scores come from?
5. 50M annotations per day: what becomes streaming, a queue, or a worker? Where does job state live?

---

## Tests you must write (in `tests/`)

With fakes of your own (`httpx.MockTransport`, monkeypatching, or a tiny local server):

1. Sample files → right `tasks_written` and Part 1 error codes; BOM/whitespace headers are clean.
2. Consensus edge cases: exactly 2/3 → agreed; fewer than 3 votes → insufficient; duplicate annotator counted once.
3. Path traversal / absolute / wrong extension → 400; missing file → 404; missing header → 422.
4. Agreed tasks make **no** LLM call; LLM 429 then OK → adjudicated; non-candidate twice → fallback.
5. Callback signature verifies against the raw body; 503 forever → 3 calls; 400 → 1 call.
6. Concurrency never exceeds 5 (count in-flight requests in your fake).

## Grading (only after you're done)

```bash
python -m pytest _grader -q                                       # both APIs faked locally
RUN_LIVE=1 OPENAI_API_KEY=sk-... python -m pytest _grader -q -m live   # Part 2 against real OpenAI
```

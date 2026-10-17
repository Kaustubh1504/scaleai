# 06: Support-ticket enrichment: CSV + Customer API + LLM (60 min)

Build it from scratch in Python. There's no starter code. Put your app in `app/main.py`
(it must expose `app = FastAPI()`) and your tests in `tests/`. Docs are fine; AI assistants are not.

| Part | Time | What |
|---|---|---|
| 1 | 20 min | `POST /enrich`: CSV → JSON, validation, safe paths, atomic write |
| 2 | 15 min | Look up each ticket's customer in a REST **Customer API**: retries, caching, error mapping |
| 3 | 20 min | OpenAI urgency per ticket (uses the customer's tier), SLA, bounded concurrency |
| — | 5 min | Discussion |

Run your server from this folder: `uvicorn app.main:app --reload`. All paths are
relative to the **process working directory**.

---

## Part 1: `POST /enrich` (20 min)

Request body (JSON):

```json
{"tickets_path": "data/tickets.csv", "output_path": "output/tickets.json"}
```

### Paths

* `tickets_path` must resolve (after `..` and symlinks) to a file **inside `./data/`** ending in `.csv`.
* `output_path` must resolve inside **`./output/`** and end in `.json`. Create missing parent
  directories under `./output/`. Overwrite an existing file.
* Absolute paths, paths that escape their root, or the wrong extension → **400**.

### Reading the CSV

* Use the header row; **don't hardcode column positions**. Extra columns pass through unchanged.
* Required headers: `ticket_id, customer_id, subject, body`. Missing header or empty file → **422**.
  Not valid UTF-8 → **422**.
* The file may start with a UTF-8 BOM. Strip whitespace from every header and every value.
* Fields may be quoted, contain commas, `""` escaped quotes, and span lines.
* Blank lines are ignored. **Row numbers** count data records from 1 (header not counted).

### Rules (checked in this order)

| Case | Action | Error code |
|---|---|---|
| wrong number of fields | skip | `malformed_row` |
| empty `ticket_id` | skip | `missing_ticket_id` |
| `ticket_id` already seen | skip (keep the first) | `duplicate_ticket_id` |

### Output file

A JSON **list** of objects in input order, each with every CSV column (stripped strings).
Parts 2 and 3 add keys to these objects. Write the file **atomically**: a reader never sees a
half-written file, a failed request leaves an existing output untouched, no temp files left behind.

### Response

`200`:

```json
{"rows_written": 11,
 "errors": [{"row": 7, "id": "K002", "error": "duplicate_ticket_id"},
            {"row": 11, "id": null, "error": "malformed_row"}]}
```

`id` is the row's `ticket_id`, or `null` for `malformed_row` / `missing_ticket_id`.
Error order doesn't matter.

Status codes: **400** bad path · **404** input file missing · **422** bad header / encoding /
body · **503** missing config (Parts 2–3) · **200** success.

With the sample file, `rows_written` is **11**.

---

## Part 2: Customer API (15 min)

Add a `"customer"` key to every row by calling the Customer API:

```
GET {CUSTOMER_API_URL}/customers/{customer_id}
X-Api-Key: {CUSTOMER_API_KEY}

200 → {"customer_id": "C01", "name": "Acme Corp", "tier": "enterprise", "region": "eu"}
404 → no such customer
```

`"customer"` is the returned object **as-is**, or `null` when there isn't a valid one.

### Configuration (read from the environment **at request time**)

| Var | Default | Notes |
|---|---|---|
| `CUSTOMER_API_URL` | — | required, e.g. `http://localhost:9000`; missing → **503** |
| `CUSTOMER_API_KEY` | — | required; missing → **503**; sent as the `X-Api-Key` header |
| `CUSTOMER_TIMEOUT` | `5` | seconds per HTTP call |
| `CUSTOMER_BACKOFF_BASE` | `0.2` | seconds; retries wait ≈ base, then 2×base |

The config check happens before any external call or file write.

### Rules (exact call budgets; the grader counts them)

| Case | Calls | Result | Error code |
|---|---|---|---|
| empty `customer_id` | **0** | `customer: null` | `missing_customer_id` |
| 200 with an object whose `tier` is `free`, `pro` or `enterprise` | — | the object | — |
| 404 | 1, no retry | `null` | `unknown_customer` |
| 429, 5xx, timeout, connection error | retry, **at most 2 retries** (3 calls) | `null` if still failing | `customer_lookup_failed` |
| other 4xx (401, 403, …) | 1, no retry | `null` | `customer_lookup_failed` |
| 200 but not JSON, not an object, or bad/missing `tier` | 1, no retry | `null` | `customer_lookup_failed` |

* **Look up each distinct `customer_id` at most once per request** (one logical lookup,
  retries included), no matter how many tickets share it. Remember `customer_id` is stripped.
* Every ticket whose lookup failed gets its own error entry.
* Never log, print or return the API key.

---

## Part 3: LLM urgency + SLA (20 min)

Add `"urgency"` and `"sla_hours"` to every row.

### Urgency (OpenAI, one logical call per ticket)

* Allowed: `low`, `medium`, `high`. The model must reply with **only** `{"urgency": "<level>"}`.
* The prompt includes the ticket's `subject`, `body` **and the customer's tier** from Part 2
  (or say it's unknown when `customer` is `null`).
* Ticket text is untrusted. Instructions inside it must not produce a value outside the allowed set.
* Can't get a valid answer → `"urgency": "unknown"` plus error `urgency_failed`. One bad ticket
  never fails the request.

Config (at request time): `OPENAI_API_KEY` (required; missing → **503**), `OPENAI_BASE_URL`
(default `https://api.openai.com/v1`, **must be honored**), `OPENAI_MODEL`, `LLM_TIMEOUT` (default
`10`), `LLM_BACKOFF_BASE` (default `0.5`). Use `httpx` or the `openai` SDK with `max_retries=0`.

Call budgets:

* 429, 5xx, timeouts, connection errors: **at most 3 retries** (4 calls), exponential backoff.
* Other 4xx: no retry → fallback.
* Invalid output (not JSON, not an object, missing/disallowed `urgency`): **one** more call,
  separate from the transport retries. Still invalid → fallback.

### SLA

`sla_hours` comes from this table. A ticket with `customer: null` uses the **free** row.
`urgency: "unknown"` → `sla_hours: null`.

| tier \ urgency | high | medium | low |
|---|---|---|---|
| enterprise | 1 | 4 | 24 |
| pro | 4 | 12 | 48 |
| free | 24 | 48 | 72 |

### Scale

`data/tickets_large.csv` has 300 tickets across 20 customers.

* At most **5** requests in flight to **each** API at once, and actually parallel.
* Output keeps input order.

---

## Discussion (5 min, out loud)

1. The Customer API is slow and rate-limited. Where would a cross-request cache live, and how long can a tier be stale?
2. A customer lookup fails: is it better to rate urgency without the tier or to skip the ticket? Why?
3. 1M tickets/day: what becomes a queue, what becomes a worker, and where does progress live?
4. How would you honor a `Retry-After` header from either API across many workers?
5. How would you check that the LLM urgency is any good, and catch it drifting?

---

## Tests you must write (in `tests/`)

With fakes for both APIs (`httpx.MockTransport`, monkeypatching, or a tiny local server):

1. Sample file → right `rows_written` and Part 1 error codes; BOM/whitespace headers are clean.
2. Path traversal / absolute / wrong extension → 400; missing file → 404; missing header → 422.
3. Two tickets with the same customer → exactly **one** Customer API call.
4. Customer 503 forever → 3 calls, `customer_lookup_failed`; 404 → 1 call, `unknown_customer`.
5. LLM 429 then OK → rated; disallowed urgency twice → `unknown`, `sla_hours: null`.
6. SLA uses the free row when the customer is `null`.
7. Concurrency never exceeds 5 (count in-flight requests in your fake).

## Grading (only after you're done)

```bash
python -m pytest _grader -q          # both APIs are faked locally; no real key needed
```

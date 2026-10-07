# prob-009 — Resilient Task Exporter (interviewer notes)

**Kind:** api-client. The candidate crawls a flaky, rate-limited API and writes
the results to disk. The weight is on failure handling and on producing output
files that are never wrong, not on aggregation (that's prob-006).
**Difficulty:** medium · **Mode:** plain Python (library + CLI) · **Starter:** skeleton · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-009 ~/interview --part1-only
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-009 python -m pytest prob-009/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-009/interviewer/hidden_tests -m "not change"   # HTTP-date change not delivered
```

The hidden tests build the API from `shared/` with **seed 91** and API key
`key_hidden_91` (the candidate's mock uses seed 9 and `key_live_exporter`).
Expected file contents are the API's own rendering of each task
(`api.rendered("tasks")`): the wire is deliberately messy and must be written
through unchanged. They call `Exporter(http, api_key, clock, out_dir).export(ids)`
and `exporter.__main__.main(argv, http=..., clock=...)`, and use `tmp_path` for `out_dir`.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–4 | Hand over `PART1.md`. Candidate reads `API.md`, `data/recorded/`, the stubs. |
| 4–18 | Id validation, cursor loop, JSONL + manifest (sha256), 404 → not_found, 401/4xx errors, tests. Reveal `PART2.md`. |
| 18–30 | Part 2: one retry loop (transient set, backoff with `+ U[0,1]`), 429 rules (Retry-After → Reset → 1 s), 8×429 cap, per-project `failed` isolation and file cleanup. |
| ~30 | **Drop the mid-part change** (below), once a scripted-429 test passes. |
| 30–38 | HTTP-date parsing against `Date`. Reveal `PART3.md`. |
| 38–55 | Part 3: atomic writer, manifest last, crash cleanup, resume by checksum, proactive throttling from `X-RateLimit-*`. |
| 55–60 | Follow-up discussion. |

If behind at minute 22, reveal Part 2 anyway. If behind at minute 45, do atomic
writes + resume and discuss throttling.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–3 | `PART1.md`, read `API.md`. |
| 3–18 | The export, the manifest, 404/401 handling. |
| 18–20 | Reveal `PART2.md`. |
| 20–27 | The retry loop for 5xx/transport/truncated with the backoff formula; one test on `clock.sleeps`. |
| 27–30 | Follow-up #3. |

Run `test_part1.py` and `test_part2.py -m "not change"`; score Part 3 categories "not observed".

## Mid-part requirement change (Part 2, ~minute 30)

Say, verbatim:

> "We just learned the API's edge proxy sometimes sends `Retry-After` as an HTTP
> date, like `Retry-After: Wed, 01 May 2024 08:00:08 GMT`, and the export host's
> clock isn't trustworthy. Support that form too, and compute the wait as that
> date minus the response's `Date` header, not your own clock."

It tests whether 429 handling was written as one small function that can grow
(`email.utils.parsedate_to_datetime`), and whether the candidate understands why
you compare against the server's `Date`. Two tests carry `@pytest.mark.change`. One
starts the clock half a second off from the `Date` header, so using the local clock gives
7.5 s instead of 8 s. Non-change tests only send numeric `Retry-After`.

## Planted bugs

None.

## Hint ladder

**Part 1**
1. "What tells you there are no more pages?" (`next_cursor is None`, not a short page)
2. "The manifest's sha256 must match the file. How do you make sure you hash exactly the bytes you wrote?"
3. "Why validate project ids before anything else?" (they become file names: `../etc`)

**Part 2**
1. "List the failure kinds from API.md. Which are retryable, which fatal, which just mean 'not found'?"
2. "429 and 5xx both get retried, but they're counted differently. Where do the two counters live?"
3. "What should be on disk for a project that failed after three pages?"

**Part 3**
1. "If the process is killed halfway through `write()`, what does the loader see?"
2. "Where must the temp file live for `os.replace` to be atomic?" (same directory, same filesystem)
3. "What evidence lets you trust last night's file without downloading it again?" (manifest + sha256)

## Common pitfalls (what the hidden tests catch)

* Re-serializing "cleaned" records instead of writing them exactly as received.
* Manifest keys or entry shapes that differ from the spec (extra keys, `status` missing on not_found).
* `generated_at` taken at the end of the run, or with `+00:00` instead of `Z`.
* Retrying 401/400 (wasted requests), or treating 404 as fatal.
* Using `time.sleep`, or exponential backoff without the stated jitter range.
* Letting 429s consume the 5 attempts, or no cap on consecutive 429s.
* A failed project leaving a partial `.jsonl` (or an old one from yesterday) in `out_dir`.
* Writing the manifest incrementally (a crash then publishes a manifest for a half-done run).
* Temp files created in `/tmp` and then `shutil.move`d (not atomic across filesystems), or temp files left behind on errors.
* Resume that trusts the manifest without re-hashing the file, or forgets that the new manifest only lists this run's projects.
* Throttling only on 200s: a 503 that says `Remaining: 0` must also make the next request wait.

## Follow-up questions

**1. "Next quarter it's 50,000 projects on one API key. How long does the export take and how do you make it fit the night?"**
Strong: estimate requests (pages ≈ tasks/25) against the quota; parallelism is
capped by the rate limit, not CPU, so use bounded concurrency with one shared
limiter driven by the `X-RateLimit-*` headers; skip unchanged projects (resume /
`updated_since`); ask for a bulk export endpoint or a higher quota; prioritize
projects the customer needs first; make it resumable across nights.

**2. "Tasks change while the export runs. What does the customer get?"**
Strong: each file is internally consistent per page but the export spans minutes or
hours, so it's not a point-in-time snapshot. Options: record a high-water mark at start
and filter `updated_at <= mark` (or `updated_since` deltas next run); keyset cursors
avoid duplicates/skips within a project; document the semantics in the manifest
(`generated_at`, per-project fetched_at).

**3. "Deliver to S3 / a warehouse stage instead of a folder."**
Strong: upload data files first, then the manifest last (the manifest is the
commit point, the loader reads only what it lists); content checksums (MD5/SHA-256)
verified on upload; multipart uploads for big files; versioned prefixes per run so a
failed run is never visible; idempotent re-runs by checksum; retention/cleanup of old runs.

## Reference solution

`reference/exporter/`: `client.py` (`TasksClient.get` with the retry loop,
`_retry_after` handling seconds, HTTP-date vs `Date`, `X-RateLimit-Reset`, 1 s
fallback, proactive `_throttle`/`_note_rate_limit` that watch every response),
`files.py` (`atomic_writer` context manager: same-dir temp, fsync, `os.replace`,
cleanup on any exception; `sha256_file`), `export.py` (`Exporter.export`: validate
ids, load previous manifest, skip verified projects, stream pages to an atomic writer
while hashing, `not_found`/`failed` entries, manifest written last).

Lines a candidate must add: Part 1 ≈ 70, Part 2 ≈ 55, Part 3 ≈ 60.

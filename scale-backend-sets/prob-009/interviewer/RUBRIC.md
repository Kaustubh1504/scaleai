# prob-009 rubric — Resilient Task Exporter

Score each category 1–4. **4** = strong hire signal, **3** = hire, **2** = lean no, **1** = no.
Write down evidence, not impressions.

| Category | 4 looks like (this problem) | 2 looks like (this problem) |
|---|---|---|
| **Correct execution** | All three parts pass on seed 91, including the HTTP-date change; zero 429s under a steady limit; crash tests leave no trace. | Export correct on a healthy API only; failed projects leave partial files; 429s retried with backoff instead of Retry-After. |
| **Debugging & unblocking** | Reproduces each failure with scripted faults and reads `api.log` timing to confirm waits; when a sha256 mismatches, diffs bytes written vs bytes hashed. | Guesses at sleeps until a test passes; can't tell why resume re-downloads everything. |
| **Systematic thinking** | Classifies every response once (retry / wait / not-found / fatal); one request loop; file writing isolated in an atomic writer; manifest as the commit point. | Status-code checks scattered across functions; retry logic duplicated for first page vs later pages; file and HTTP code tangled. |
| **Production quality** | Atomic same-directory writes with cleanup in `finally`/`except BaseException`; ids validated as file names; bounded retries and 429 cap; injected clock; nothing half-published. | `open(path, "w")` directly; temp files in `/tmp`; unbounded loops on 429; bare excepts that mark everything "failed". |
| **Testing** | Tests per failure kind with `FaultConfig(scripted=...)`, asserting `clock.sleeps` ranges and `api.log`; a crash-in-the-middle test (`on_request` raising) and a resume test that modifies a file. | Happy-path test only; no test touches the filesystem failure paths. |
| **End-to-end ownership** | Runs the CLI against the real mock server with `--failure-rate` and `--rate-limit`, checks exit codes and the manifest; mentions what the loader will see at each moment. | Never runs the CLI; doesn't look at what's actually on disk after a failure. |
| **Communication** | Explains why `Date` beats the local clock, why the manifest goes last, and what "atomic" guarantees (and doesn't, e.g. across filesystems). | Can't articulate the difference between a retryable and a fatal error; silent through Part 3. |

## Hidden-test mapping

| Test file | Covers |
|---|---|
| `test_part1.py` | every file matches the wire, records unchanged, manifest shape/order/`generated_at`, newline handling, each page once with `limit=25`, API key header, not_found without file, empty project, `out_dir` creation, 401 → `AuthError` + no manifest, other 4xx → `ApiError`, unsafe ids before any request, CLI exit codes |
| `test_part2.py` | 5xx backoff ranges and jitter, 5-attempt cap + continue, mid-crawl failure leaves no file, stale files removed, truncated/timeout/connection errors transient, 401/4xx not retried, Retry-After exact, Reset fallback, 1 s fallback, 429s don't use attempts, 8×429 fails the project, real limit waited out, CLI exit 2, HTTP-date vs `Date` (`change` ×2) |
| `test_part3.py` | proactive throttling (no 429s, exact wait, follows error responses, under random faults), resume skip/re-export/retry/different list/unreadable manifest, crash mid-project, failing manifest/file replace, no temp files |

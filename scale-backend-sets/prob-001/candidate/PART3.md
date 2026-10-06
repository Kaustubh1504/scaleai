# Part 3: Hardening for production traffic (about 20 minutes)

The service is going live for customers who upload thousands of tickets at a
time, and the model provider enforces rate limits.

## 1. Backoff between attempts

Before attempt `n + 1` (after attempt `n` failed with a retryable error or an
invalid output), wait using the app's `clock` (`clock.sleep(seconds)`, never
`time.sleep`):

* after an `LLMRateLimitError`: exactly `err.retry_after` seconds;
* otherwise: a random duration uniformly drawn from `[d / 2, d]`, where
  `d = min(8, 0.5 * 2 ** (n - 1))` seconds.

Do not wait after the final attempt, after a success, or after a
non-retryable error.

## 2. Bounded concurrency

Classify up to `max_concurrency` tickets at the same time (the `create_app`
argument, default 4). Never exceed it. The results order is still upload order.

## 3. Idempotent re-runs

Calling `POST /uploads/{upload_id}/classify` again must not call the LLM for
tickets that are already `classified`. Only tickets that failed (or were never
classified) are attempted again. The response and the persisted file contain
the merged results for all tickets; `attempts` for a re-attempted ticket counts
the calls made in the latest run.

## 4. Discussion (no code required)

Be ready to talk about:

* the same ticket getting different labels on different runs;
* sharing the provider's rate limit across many instances of this service;
* what changes when uploads are 100x larger and classification takes minutes.

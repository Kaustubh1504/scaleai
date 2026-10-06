# Pre-label Cache

When an annotator opens a task, the labeling tool asks a model server for **pre-labels**
(a model's first guess that the annotator then corrects). Model calls are slow, so the
tool keeps a time-to-live (TTL) cache in front of the model server. This repo replays a
recorded request log against that cache and reports what happened.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/requests.csv`: the request log, in time order. `op` is `fetch` or `publish`.
- `data/config.json`: `default_ttl_seconds` plus a per-model `ttl_seconds` override map.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task ids: trim and upper-case (`t01 ` → `T01`). Model names: trim and lower-case
  (`OCR-v1` → `ocr-v1`), in both the log and the config. Locales: trim and lower-case;
  a blank locale on a `fetch` row means `en-us`.
- `op`: trim and lower-case.
- `ts` uses one of `2026-03-02 09:00:00`, `2026-03-02T09:00:00` or
  `03/02/2026 09:00:00` (month/day/year).
- TTL values in the config may be numbers or numeric strings.

### The model server

- Every model starts at version `1`. A `publish` row bumps that model's version by one.
- A call for `(task, model, locale)` returns the pre-label id
  `"{model}@{version}/{task}/{locale}"`, using the model's current version.

### The cache

1. A cached pre-label is identified by **task id, model and locale** together. A pre-label
   for one locale must never be served for another.
2. The TTL for a model is its `ttl_seconds` override, or `default_ttl_seconds` if it has
   none.
3. An entry stored at time `t` with TTL `T` expires at `t + T`. It is **fresh** while
   `now < t + T`. At exactly `t + T` it is expired.
4. `fetch`: if a fresh entry exists, the result is a `hit` and the cached value is
   returned. A hit does **not** extend the entry's lifetime. Otherwise the result is a
   `miss`: the model server is called and the new value is stored with `stored_at = now`.
5. `publish`: bump the model's version and remove every cached entry for that model.

### Report

`labelcache.reports.build_report()` returns:

- `outcomes`: one item per `fetch` row, in log order: `ts`, `task_id`, `model`,
  `locale`, `result` (`hit`/`miss`) and `value`.
- `models`: for each model seen in the log, `hits`, `misses`, `version` (the final
  version) and `last_refresh` (the `ts` of that model's most recent miss, or `None`).
- `snapshot`: the entries still fresh at the `ts` of the last log row, sorted by model,
  then task id, then locale. Each has `task_id`, `model`, `locale`, `value` and
  `expires_at`.

`labelcache.reports.report_json()` is the same report as a JSON string. Every timestamp
in the report, in both forms, is written as ISO 8601 `YYYY-MM-DDTHH:MM:SS`
(e.g. `2026-03-02T09:00:00`).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.

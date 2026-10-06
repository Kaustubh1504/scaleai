# Guideline Cache

Annotation tools ask a guideline service for the label set of a project in a given
locale many times a minute. The source of truth (the "origin") is slow, so the service
keeps a TTL cache in front of it. Some clients also get extra, client-specific labels
added to the response. This tool replays a request trace against the service using the
trace timestamps as the clock, and reports what each request got back.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/guidelines.json`: every published guideline version (`project`, `locale`,
  `version`, `published_at`, `labels`).
- `data/config.json`: `ttl_s` (seconds, per project), `default_ttl_s`, and `overrides`
  (client → project → extra labels).
- `data/trace.csv`: the requests (`request_id`, `ts`, `client`, `project`, `locale`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Projects, clients and locales: trim and lower-case. A blank locale means `en`.
  Request ids: trim and upper-case. Labels: trim.
- Timestamps use one of `2026-06-01 09:00:00`, `06/01/2026 09:00:00` (month/day/year),
  `2026-06-01T09:00:00` or a bare date `2026-05-20` (midnight).
- Requests are replayed in `ts` order.

### Origin

- A fetch for (project, locale) at time `now` returns the **highest version** of that
  project and locale whose `published_at` is at or before `now`. If there is none, the
  request's outcome is `not_found` and nothing is cached.

### Cache

- Entries are keyed by **project and locale**: the French and English label sets of a
  project are different entries.
- An entry stored at time `t` with TTL `ttl` is fresh while `now − t < ttl`. At exactly
  `ttl` seconds old it has expired, so that request is a `miss` and refetches.
- TTL is `ttl_s[project]`, or `default_ttl_s` for projects not listed.
- A `hit` serves the cached entry; a `miss` fetches from the origin and caches the result.

### Overrides

- After the lookup, the client's extra labels for that project (if any) are appended to
  **that response only**. They must never leak into the cache or into other clients'
  responses, and a client must not get them twice.

### Report

`guidecache.reports.build_report()` returns:

- `lookups`: request id → `project`, `outcome` (`hit`, `miss` or `not_found`),
  `version` and `locale` of the label set served (`None` when not found);
- `payloads`: request id → the labels served (with overrides), or `None`;
- `origin_fetches`: project → number of origin fetches.

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

# Part 1: Nightly task export (about 20 minutes)

A customer loads our data into their warehouse every night. They want, for
each of their projects, a JSONL file with every task, plus a manifest that
says what was exported. The data comes from the Tasks API (`API.md`).

## Contract (keep these signatures; tests call them)

```python
from exporter.client import TasksClient, ApiError, AuthError
from exporter.export import Exporter, ExportSummary

exporter = Exporter(http, api_key, clock, out_dir)   # http: httpx.Client with base_url set
summary = exporter.export(["prj_01", "prj_02"])      # -> ExportSummary(generated_at, projects)
```

* Send every request through the given `http` client, with the `X-API-Key` header.
  Use `clock` for any time you need.
* `python -m exporter --project prj_01 --project prj_02 --out exports/` is
  already wired up in `exporter/__main__.py` (exit code 0 if every project is
  `complete`, 2 if some project is not, 1 on a fatal error).

## Validation

Every project id must be a non-empty string of letters, digits, `_` and `-`
(they become file names). Otherwise `export()` raises `ValueError` **before
making any request**.

## Fetching

For each project, **in the order given**, read all of its tasks from
`GET /v1/projects/{id}/tasks` with `limit=25`, following `next_cursor` until it
is `null`. Fetch each page once.

## Output files

Create `out_dir` (and its parents) if needed.

* `out_dir/<project_id>.jsonl`: one task per line, in API order, each line
  `json.dumps(record)` + `"\n"`, where `record` is the task **exactly as the
  API returned it** (do not clean or retype fields; see "Data quality" in
  `API.md`). A project with no tasks gets an empty file.
* `out_dir/manifest.json`:

```json
{
  "generated_at": "2024-05-01T08:00:00Z",
  "projects": {
    "prj_01": {"status": "complete", "tasks": 51, "file": "prj_01.jsonl", "sha256": "<hex>"},
    "prj_99": {"status": "not_found"}
  }
}
```

* `generated_at`: the clock's time when `export()` starts, formatted
  `YYYY-MM-DDTHH:MM:SSZ`.
* `projects`: one entry per requested project, in the requested order, with
  exactly the keys shown. `sha256` is the hex SHA-256 of the file's bytes.
* A `404` for the project means `{"status": "not_found"}` and **no file**
  (delete one left over from an earlier run).
* `export()` returns `ExportSummary(generated_at, projects)` with the same
  values as the manifest.

## Errors (no retries yet)

* `401` raises `AuthError` (a subclass of `ApiError`).
* Any other non-2xx response (except the 404 above) raises `ApiError` with
  `.status` and `.path` set.
* These errors are fatal: they propagate out of `export()`, and no manifest is
  written for that run.

Write tests against `mock_services.api.make_api()` (see its docstring). They
should not depend on one seed's exact data.

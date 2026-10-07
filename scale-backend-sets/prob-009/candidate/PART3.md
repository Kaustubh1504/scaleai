# Part 3: Never a half-written file, never wasted work (about 20 minutes)

The warehouse loader picks up whatever is in `out_dir`. Last week the export
host was killed mid-run and the loader ingested a truncated file. The nightly
job also wastes the rate limit re-downloading projects that haven't changed.

## 1. Atomic results

* Write every output file (each `.jsonl` and `manifest.json`) to a temporary
  file **in the same directory**, then rename it over the target with
  `os.replace`. A reader must only ever see the previous complete file or the
  new complete file.
* Write `manifest.json` **once, after all requested projects have been
  processed**.
* If the run dies part-way (any exception other than the handled API errors,
  such as a crash in the HTTP layer, or an `OSError` while writing), the
  exception propagates and `out_dir` still holds the previous run's manifest and
  files, unchanged. No partial `.jsonl` and **no temporary files** are left
  behind. A project finished before the crash may already have its new file.

## 2. Resume

When `out_dir` already has a manifest, a project whose previous entry is
`"complete"`, whose `file` is `<project_id>.jsonl`, and whose file's SHA-256
still matches the recorded `sha256` is **not fetched again**: its old entry is
copied into the new manifest. Everything else (failed, not_found, missing or
modified file, or a project not in the old manifest) is exported normally.

* The new manifest lists only the projects requested in this run, in this run's order.
* `generated_at` is this run's start time.
* A manifest that can't be read or parsed counts as no manifest.

## 3. Don't trigger the rate limit

Every response carries `X-RateLimit-Remaining` and `X-RateLimit-Reset` (see
`API.md`). When a response (success **or** error) says `Remaining` is `0`, wait
until `Reset` (with `clock.sleep`) before sending the next request. With this,
an export under a steady rate limit gets **no** 429s at all.

## 4. Discussion (no code required)

Be ready to talk about:

* exporting 50,000 projects every night within one API key's rate limit;
* what the export means if tasks change while it runs, and how to give the
  customer a consistent snapshot;
* delivering to S3 or a warehouse instead of a local folder: atomicity,
  checksums, and in what order to publish data files and the manifest.

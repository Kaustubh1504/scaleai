# Speaker-Disjoint Speech Splits

The speech team is building a voice-command dataset. Each clip was read by one speaker,
and a speaker must never appear in more than one split, or the eval numbers leak. This
tool cleans the clip export, assigns every speaker to `train`, `val` or `test`
(stratified by accent) and summarises the splits.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/speakers.csv`: the speaker registry (`speaker_id`, `accent`, `held_out`, `region`).
- `data/clips.csv`: one row per recorded clip.
- `data/config.json`: hash seed, split percentages and the allowed clip duration.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Speaker ids and clip ids: trim and upper-case (`s02` → `S02`). Accents: trim and
  lower-case (`US` → `us`).
- `consent` and `held_out` are true for `y`, `yes`, `true` or `1` (any case). Anything
  else, including a blank cell, is false.
- `recorded_on` uses `2026-04-28`, `29/04/2026` (**day/month/year**, the studio is in
  London) or `30 Apr 2026`.
- `duration_ms` may have surrounding spaces.
- A transcript is compared after normalisation: lower-case, every character that is not a
  letter, digit, underscore, apostrophe or whitespace becomes a space, then runs of
  whitespace collapse to one space and the ends are trimmed.

### Exclusions

Each clip gets the reason of the **first** rule it fails, in this order:

1. `unknown_speaker`: the speaker is not in the registry.
2. `no_consent`: consent is false.
3. `no_transcript`: the normalised transcript is empty.
4. `duration`: `duration_ms` is outside `min`–`max` from the config. Both limits are
   allowed (a clip of exactly `min` or exactly `max` ms is kept).
5. `duplicate`: among the clips that passed rules 1–4, a speaker may have several clips
   with the same normalised transcript. Keep only the one with the earliest
   `recorded_on` (ties: lowest clip id); the others are duplicates.

### Split assignment

6. Only speakers with at least one kept clip take part. They are grouped into **strata**
   by accent.
7. In each stratum, every `held_out` speaker goes to `test`.
8. The remaining speakers of the stratum (call their number `n`) are ordered by
   `sha256("<seed>:<speaker_id>")` hex digest, ascending. The first
   `n × test_percent // 100` go to `test`, the next `n × val_percent // 100` go to `val`
   and the rest go to `train`.
9. Every kept clip goes to its speaker's split.

### Report

`voxsplit.reports.build_report()` returns:

- `excluded`: clip id → reason.
- `strata`: accent → number of participating speakers (held-out ones included).
- `assignment`: speaker id → split.
- `splits`: for each of `train`, `val`, `test`: `clips` (sorted ids), `minutes` (total
  duration in minutes, rounded to 2 decimals) and `accents` (accent → number of clips).

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

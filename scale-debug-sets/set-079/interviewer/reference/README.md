# Judge Score Rollup

Several LLM judges grade each model response against a rubric. Their raw replies are
free text: sometimes JSON, sometimes a "Score: 4/5" line, sometimes a pass/fail verdict.
This tool reads the replies, normalises them to a 0–1 score, combines judges per sample,
and builds a weighted leaderboard plus per-category averages.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/rubric.json`: `category` and its `weight` (a number or numeric string).
- `data/samples.csv`: `sample_id`, `model`, `category`, `prompt`.
- `data/judgments.jsonl`: one JSON object per line: `id`, `sample`, `judge`, `output`
  (the judge's raw reply).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Ids, model names, judge names and categories: trim and lower-case.
- Samples whose category is not in the rubric are ignored. Judgments for unknown samples
  are ignored (they are not failures).

### Reading a judge reply

Try these in order:

1. A JSON object (possibly inside a ```` ``` ```` fence, possibly with prose around it)
   with a `score` key: score = `score` ÷ `scale`, where `scale` defaults to 10.
2. A `Score: N/D` or `Rating: N/D` phrase (any case, `:` or `=`): score = N ÷ D.
3. A `Verdict: PASS` / `Verdict: FAIL` phrase: 1.0 / 0.0.

The reply is a **parse failure** when none of these apply, when a value is not numeric,
or when the score falls outside 0–1. A line of `judgments.jsonl` that is not valid JSON is
also a parse failure, reported as `line-<n>` (1-based line number), because there is no
id to report.

### Aggregation

- A sample's score is the **median** of its readable judgments. Samples with none are
  **unscored**.
- A model's leaderboard score is the weighted mean of its scored samples' scores, with
  each sample weighted by its category weight.
- A category's `mean` is the plain mean of its scored samples' scores (all models), and
  `n` is how many there are.
- Rounding is for display only. Every calculation uses unrounded sample scores, and only
  the final values are rounded.

### Report

`judgescore.reports.build_report()` returns:

- `samples`: scored sample → score rounded to 2 decimals;
- `unscored`: sorted sample ids;
- `parse_failures`: sorted judgment ids (and `line-<n>` entries);
- `judges`: judge → number of readable judgments;
- `leaderboard`: model → score rounded to 3 decimals;
- `categories`: category → `{"n", "mean"}` (mean rounded to 3 decimals), for categories
  with at least one scored sample.

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

# Multiple-Choice Eval Scorer

An eval harness ran two models over a bank of multiple-choice questions. The harness
retries failed calls, so a model can have several attempts per question. This tool picks
the attempt to grade for each (model, question), parses the letter the model chose, and
produces weighted accuracy, a per-category breakdown and a leaderboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/items.json`: the question bank (`id`, `category`, `answer`, `weight`).
- `data/attempts.csv`: one row per call the harness made (`model`, `item_id`,
  `attempt`, `status`, `output`, `latency_ms`). Rows are not guaranteed to be in
  attempt order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids: trim and upper-case (` q03` → `Q03`). Model names: trim and lower-case.
  Categories: trim and lower-case. Answers: trim and upper-case.
- `weight` may be a number or a numeric string. A missing or blank weight means `1.0`.
- `status` (trim, any case): `ok` or `success` means **ok**; `timeout` or `timed_out`
  means **timeout**; anything else, including a blank cell or an HTTP code like `500`,
  means **error**.

### Choosing the graded attempt

1. For each (model, item), only attempts with status **ok** are candidates. The
   candidate with the highest `attempt` number is graded.
2. If a model has no ok attempt for an item, the item is **failed** for that model.

### Parsing the output

3. The chosen letter is taken from the **last** `Answer` marker in the output: the word
   `answer` (any case), an optional `:` or `=`, then a letter A–D, optionally in
   parentheses. Models sometimes revise themselves, so earlier markers are ignored.
4. If there is no marker, an output that is just one letter A–D (after trimming;
   optionally in parentheses and/or followed by a period) counts as that letter.
5. Otherwise the item is **unparsed** for that model.

### Scoring

6. An item is **correct** when the parsed letter equals the item's answer. Mismatched,
   unparsed and failed items all earn 0.
7. `accuracy` = total weight of correct items ÷ total weight of **all** items in the
   bank, rounded to 3 decimals. Failed and unparsed items stay in the denominator.
8. `by_category`: the same ratio restricted to each category, rounded to 3 decimals.

### Report

`evalscore.reports.build_report()` returns:

- `models`: for each model, `accuracy`, `correct`, `unparsed`, `failed` (sorted item
  ids) and `by_category`.
- `status_counts`: for each model, the number of attempt rows with each status
  (`ok`, `error`, `timeout`).
- `leaderboard`: model names by accuracy, highest first (ties: name ascending).

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

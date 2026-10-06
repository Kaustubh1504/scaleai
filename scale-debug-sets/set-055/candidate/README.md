# Multiple-Choice Eval Scorer

Four models answered the same twelve multiple-choice questions. Every call to a model is
logged as an **attempt**: some attempts timed out or were rate-limited and were retried,
and some answers came from a response cache. This tool picks the attempt that counts for
each model and question, pulls the chosen letter out of the model's free-text output,
grades it, and builds a weighted leaderboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/items.csv`: `item_id`, `category`, `gold` (A–D) and `weight`.
- `data/responses/<model>.jsonl`: one JSON object per attempt with `model`, `item`,
  `attempt` (1, 2, ...), `status` and `output`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids and gold letters: trim and upper-case. Model names, categories and statuses:
  trim and lower-case.
- `weight` is a whole number of points. A blank weight means 1. A weight of `0` is a
  real weight: calibration items count for nothing in the weighted score.

### Which attempt counts

1. Only attempts with status `ok` or `cached` are **successful**. `error`, `timeout`
   and `rate_limited` never count, whatever their output says.
2. For each model and item, the successful attempt with the highest `attempt` number
   counts. If there is none, the item is **errored** for that model.

### Reading the answer

Apply the first rule that fits the trimmed output:

1. Output starting with `{` is JSON. Its `answer` must be a single letter A–D (any
   case); otherwise there is no answer.
2. Otherwise look for answer markers such as `Answer: B`, `answer is (c)` or
   `Answer = D` (any case). If there are several, the **last** one wins, because models
   often think out loud before committing.
3. Otherwise an output that is just a letter, like `B`, `(b)` or `B.`, is that letter.
4. Otherwise the item is **unparsed**.

An item is `correct` when the letter equals the gold letter, and a `miss` otherwise.

### Report

`evalscore.reports.build_report()` returns, per model (sorted by name):

- `correct`: sorted ids of correct items;
- `unscored`: `{"errored": [...], "unparsed": [...]}`, sorted ids;
- `weighted_scores`: total weight of correct items ÷ total weight of all items, rounded
  to 3 decimals;
- `category_accuracy`: per category, correct items ÷ all items in that category
  (errored and unparsed count as not correct), rounded to 3 decimals;
- `leaderboard`: model names by weighted score (highest first). Ties go to the model with
  more correct items, then to the alphabetically first name.

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

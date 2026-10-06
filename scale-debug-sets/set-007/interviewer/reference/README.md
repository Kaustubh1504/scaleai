# Multiple-Choice Eval Scorer

Three models answered the same 12 multiple-choice benchmark items. Their raw outputs are
saved in `data/responses.jsonl`. This tool pulls the chosen letter out of each output,
grades it against the gold answer, and builds per-model stats and a leaderboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/items.csv`: `item_id`, `category`, `gold` (a letter A–D) and `weight` (an integer).
- `data/responses.jsonl`: one JSON object per line with `id`, `model`, `item_id`,
  `output` (the model's raw text) and `latency_ms` (a number, sometimes written as a string).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Response ids, model names, item ids and categories: trim and lower-case.
- Gold letters: trim and upper-case.

### Parsing an output

1. An answer tag is the word `answer` (any case) followed by `:`, optional spaces and a
   letter A–D, optionally in parentheses: `Answer: B`, `answer: (D)`, `ANSWER: C.`
   (`Final Answer: C` contains a tag too.)
2. If there are several tags, the **last** one is the answer.
3. Flags, per response:
   - `no_answer`: no tag at all (the answer is `None`);
   - `multiple_answers`: the tags name more than one distinct letter. Repeating the same
     letter is not flagged.
   A response with neither condition has an empty flag list.

### Grading and stats

4. A response is correct when its answer equals the item's gold letter.
5. Per model:
   - `accuracy`: total weight of correctly answered items ÷ total weight of the items it
     answered, rounded to 3 decimals;
   - `parse_failures`: responses whose answer is `None`;
   - `mean_latency_ms`: mean latency, rounded to 1 decimal;
   - `by_category`: category → number of correct responses (categories with no correct
     response are left out).
6. Leaderboard: models by accuracy, highest first. On equal accuracy the lower
   `mean_latency_ms` ranks higher; if that also ties, alphabetical by model name.

### Report

`evalscore.reports.build_report()` returns `responses` (per response id: `model`, `item`,
`category`, `weight`, `latency_ms`, `answer`, `correct`, `flags`), `models` (the stats
above) and `leaderboard` (a list of model names).

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

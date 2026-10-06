# set-035 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does load_comparisons return?

A list of valid `Comparison` objects in file order and a Counter of exclusion reasons (`skipped`, `rater`, `invalid`). For a tie, `winner` is None; otherwise it is the winning model's cleaned name.

### 2. How are flags like skipped parsed?

`flag()` returns JSON booleans as is; anything else is cleaned, lower-cased and checked against {true, yes, y, 1}.

### 3. What does win_rates compute?

It walks the comparisons and fills three Counters: `games` (both models), `ties` (both models on a tie) and `wins` (on a decisive result). The rate per model is (wins + 0.5 × ties) / games, rounded to 3 decimals. It returns (games, rates).

### 4. In what order does elo_ratings apply comparisons?

It sorts the valid comparisons with `key=lambda c: c.round`; sorting is stable, so within the same round value the file order is kept.

### 5. Where is the minimum-games rule applied?

In `reports.leaderboard`, which filters models by `games[m]` against `MIN_GAMES` (11) and sorts the rest by (-rating, name). Elo and win rates are still reported for every model.

### 6. Is the Elo update zero-sum?

Yes. Model a gains K × (Sa − Ea) and model b gains K × ((1 − Sa) − (1 − Ea)), which is the negative of a's change, so the ratings always add up to 1000 × the number of models.

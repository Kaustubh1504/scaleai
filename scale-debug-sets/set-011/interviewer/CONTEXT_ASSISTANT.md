# set-011 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads the registry from models.json (`load_models`), then `load_comparisons` reads the CSV, keeps rows with a recognised winner between registered models, and sorts them by `rated_at`. `win_table` builds games/wins/ties per model, `elo_ratings` replays the games for Elo, and `leaderboard` filters and sorts the models.

### 2. What does load_models return?

A dict mapping the normalised (trimmed, lower-cased) model id to its display name. Only the keys are used for registry checks.

### 3. Which rows does load_comparisons drop?

Rows whose normalised `winner` is not in `OUTCOMES` (a, b, tie, draw, both_bad), which includes blanks, and rows where either model id is not a registry key. The rest are returned sorted by `rated_at`; Python's sort is stable, so equal times keep file order.

### 4. How does elo_ratings treat both_bad games?

It skips any comparison whose winner is not a key of `SCORE_FOR_A`, and both_bad is not a key. All other games call `update()` with the score for model_a.

### 5. Where is win_rate computed and how is it rounded?

It is a property on `ModelStats` in models.py: (wins + 0.5 × ties) / games, rounded to 3 decimals, and 0.0 when games is 0.

### 6. Which models appear in the report's models section?

Every registry model whose `games` is non-zero, in registry order. The leaderboard is computed separately from the same table and ratings.

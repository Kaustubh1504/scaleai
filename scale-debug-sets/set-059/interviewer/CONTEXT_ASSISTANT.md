# set-059 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do?

load_raters returns the set of qualified rater ids; read_comparisons filters and resolves rows to Comparison objects; latest_only dedupes and returns them in (created_at, row) order; then elo, win_rates and contested are computed from that list, and the leaderboard is sorted from the Elo dict.

### 2. What does a Comparison look like?

prompt_id, rater, pair (the two model ids as a sorted tuple), winner (a model id, or None for a tie), created_at (datetime) and row (the CSV line number, header = 1).

### 3. How does read_comparisons decide which rows to keep?

It cleans the rater id and the winner letter, and skips the row if the rater is not in the qualified set or the letter isn't a/b/tie. It then reads the swapped flag, flips a<->b if set, and maps the letter to model_a/model_b (tie -> None).

### 4. How does latest_only break ties between duplicate judgements?

It keys by (rater, prompt_id, pair) and replaces the stored comparison when (created_at, row) is greater, so later times win and, at equal times, the later CSV row wins.

### 5. How is Elo updated per comparison?

With a, b = c.pair, score_a is 1, 0 or 0.5, delta = K * (score_a - expected(Ra, Rb)), then Ra += delta and Rb -= delta. Ratings start at 1000 via a defaultdict and are rounded to 1 decimal at the end.

### 6. How does contested() group comparisons?

It uses itertools.groupby with the key (prompt_id, pair) and adds the prompt id when a group's set of winners has more than one value (None counts as a value).

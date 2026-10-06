# set-087 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the order of steps inside build_dataset()?

For each conversation it looks up the source (unknown -> rejected, not included -> skipped), then calls `normalise_turns`, `merge_consecutive`, `split_pairs`, and `fit_budget`. If the returned total is still above `max_tokens` the conversation is rejected as `too_long`; otherwise an example is stored and its tags are recorded for the summary.

### 2. What does normalise_turns return for a turn whose role is 'tool'?

roles.csv maps `tool` (and `function`) to `tool`, which is not in `ROLES`, so the turn is skipped and nothing is appended for it.

### 3. Where does a blank max_tokens value end up?

`load_sources` reads the cell with `clean()`. If it is empty it uses `DEFAULT_MAX_TOKENS` (64), otherwise `int()` of the cell. vendor-b, sharegpt, internal-qa and legacy-chat use the default.

### 4. What does fit_budget return?

A tuple `(pairs[start:], start, total)`: the kept pairs, how many leading pairs were dropped, and the token total of the system turn plus the kept pairs. It never drops the last pair, because the loop stops when `start` reaches `len(pairs) - 1`.

### 5. How does split_pairs decide what the system turn is?

If the first turn's role is `system` it is returned separately and the rest is the body. Leading non-user turns and trailing non-assistant turns are popped from the body, and the remainder is paired two at a time.

### 6. Which examples feed tag_counts?

Only kept examples. `tags_by_id` is filled when an example is stored, and `summarize` counts every tag in those lists with a Counter, sorted by tag.

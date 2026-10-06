# set-079 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does load_judgments return?

A tuple (judgments, failures). judgments is a list of Judgment(judgment_id, sample_id, judge, score) for readable replies on known samples. failures is a list of ids whose reply normalised_score could not read, plus entries for lines that could not be decoded.

### 2. In what order does normalised_score try the formats?

First a JSON object (fenced or bare) with a 'score' key, using 'scale' with a default of 10. Then extract_fraction for 'Score/Rating: N/D'. Then the VERDICT regex for pass/fail. A final range check rejects den <= 0 or num outside 0..den.

### 3. What is the difference between `scores` and `shown` in build_report?

`scores` comes from sample_scores: sample id -> unrounded median. `shown` is a new dict with each value rounded to 2 decimals, sorted by sample id, and is what the report returns as 'samples'.

### 4. How does weighted_mean work?

It takes a list of Sample objects, a sample-id -> score mapping and the category weights, and returns sum(weight[category] * score) / sum(weight[category]) over those samples.

### 5. How many times is group_by called per build_report?

Twice: once with key=model (by_model, used for the leaderboard) and once with key=category (by_category, used for the categories table). Neither call passes `into`.

### 6. Which samples have only one readable judgment?

s05 (j10 has no score phrase), s08 (j15 is 11/10), s11 (judge-b's line is malformed), s15, s17 (j32's score is 'high') and s18. s19's only reply is unreadable and s20 has none.

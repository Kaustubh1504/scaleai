# set-025 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do?

It loads contributors, builds best scores from assessments.csv with best_scores, loads projects, calls allocate, then computes used hours, utilization and idle over active contributors with capacity > 0.

### 2. What does best_scores return and how are blank scores handled?

A dict contributor_id -> {skill: score}. Rows with a blank score are skipped. The remaining score strings are collected per contributor and skill, then reduced to one int per skill.

### 3. Where is the region rule applied?

rules.region_ok, called from is_eligible after the active/capacity check and before the score check. load_projects turns a blank region into 'any'.

### 4. How does allocate track hours?

`remaining` starts as each contributor's capacity. For each project in project_order it gets the eligible list, sorts it with candidate_order, and walks it, subtracting the hours given. Leftover need goes into `unfilled`.

### 5. What does project_order sort by?

(-priority, id), so higher priority numbers come first and ties go to the lower id.

### 6. Which contributors appear in utilization?

Only those with active True and capacity > 0, so C06 (0 hours) and C07 (inactive) are left out.

# set-070 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, in order?

It loads policies, reviewers and predictions (the loader fills a blank priority from the task policy), routes every prediction with router.route_all, assigns review items with assign_reviewers (which sets item.reviewer and returns the backlog), builds worklists and calls summarize.

### 2. How does router.route pick a reason?

It returns at the first matching check: sensitive, label in policy.always_review, missing confidence, confidence below policy.threshold, and otherwise auto_accept with reason 'confident'. Each result is a Routed object holding a Decision enum member.

### 3. What does parse_flag accept?

It trims and lower-cases the value and returns True only for 'yes', 'y', 'true' or '1'.

### 4. How are worklists ordered?

build_worklists groups assigned items by reviewer, then runs two stable sorts: first with a lambda key on one prediction field, then with urgency(), which returns a (priority, confidence) tuple where a missing confidence becomes -1.0.

### 5. Which reviewers can take toxicity items?

In reviewers.json: r01 (capacity 4, also pii), r02 (capacity 3) and r05 (capacity 2, also caption). r09 also has the skill but is inactive.

### 6. What is Decision?

A plain Enum in models.py with members AUTO_ACCEPT = 'auto_accept' and HUMAN_REVIEW = 'human_review'. The report's routing section prints decision.value.

### 7. How is mean_review_confidence computed?

summarize builds a list of confidences, skipping None, averages it and rounds to 3 decimals. It returns None if the list is empty.

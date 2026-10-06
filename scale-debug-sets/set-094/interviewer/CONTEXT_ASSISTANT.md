# set-094 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() return and in what order are things computed?

It loads the policy, predictions, reviewers and reviews, routes every prediction with `router.route_all`, passes the decisions to `assign.assign_expert_queue`, and computes `calibration.model_calibration` and `label_confusions` from the reviews. Calibration does not depend on routing or assignment.

### 2. What does decide() check, in order?

Unknown label, then sensitive, then flagged, then missing confidence. After that it compares the confidence with `policy.threshold_for(rule)` to choose `auto`/`confident` or the fallback/`low_confidence`, and finally applies the legacy-model override.

### 3. What is the Route type?

`enums.Route` is a plain `Enum` with members AUTO='auto', EXPERT='expert' and CROWD='crowd'. Decisions store the member; reports.py writes `route.value` into the output.

### 4. How does assign_expert_queue build the pools?

It groups (prediction, decision) pairs whose route is EXPERT by `pred.lang`. For each pool, in sorted pool order, it takes reviewers whose `pool` equals the pool name, sorts the items with `queue_order`, and assigns each item to the eligible reviewer with the lowest `(load, reviewer_id)`, or adds it to that pool's backlog.

### 5. Does reviewer load carry across pools?

Load lives on each Reviewer object and starts at 0 when loaded. A reviewer is only considered for the pool their `pool` field matches, so in practice each reviewer's load comes from one pool.

### 6. Which reviews does the calibration use?

`load_reviews` drops rows whose confidence is blank. Everything else is kept in file order, with models and labels lower-cased.

### 7. What does label_confusions return for a label the humans always agreed with?

Every model_label seen gets a Counter, even with no disagreements. A label whose Counter is empty maps to None.

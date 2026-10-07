# set-070 interviewer notes

**Scenario:** Route model predictions to auto-accept or human review by sensitivity, label policy and confidence threshold, assign review items to skilled reviewers with capacity, order worklists by urgency (priority 1 = most urgent), and summarise the run.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Zero confidence treated as missing

1. **Nudge:** T04's confidence column is 0, not blank. What reason does it get?
2. **Area:** parse_confidence is VERIFIED. Look at how router.route tests for a missing confidence.
3. **Exact:** Use `if pred.confidence is None:`.

### B2: Sensitive flag parsed with bool()

1. **Nudge:** C02 is marked 'no' in the sensitive column but is routed as sensitive.
2. **Area:** Follow the sensitive column from load_predictions into parse_flag and compare with the README flag rule.
3. **Exact:** parse_flag returns `bool(clean(value))`; it should return `clean(value).lower() in {"yes", "y", "true", "1"}`.

### B3: Priority sorted as if higher is more urgent

1. **Nudge:** In r01's list, the priority-2 PII items come before T06 and P05, which are priority 1.
2. **Area:** Check the urgency key against the README's priority convention.
3. **Exact:** Return (pred.priority, confidence), with no negation.

### B4: Equal-urgency tie broken by item id

1. **Nudge:** C09 and C06 have the same priority and confidence. Which one is older?
2. **Area:** Look at the first sort pass in build_worklists. What does it sort by?
3. **Exact:** Sort the first pass by i.prediction.created_at, not item_id.

### B5: Decision compared with a plain string

1. **Nudge:** Every auto_accept_rate is 0.0, yet routing shows 9 auto-accepted items.
2. **Area:** Look at how summarize decides which items were auto-accepted.
3. **Exact:** Compare with the enum: r.decision is Decision.AUTO_ACCEPT (or r.decision.value == 'auto_accept').

### B6: Mean confidence over all items

1. **Nudge:** mean_review_confidence is higher than the review items alone could give.
2. **Area:** Check which collection the scored list is built from.
3. **Exact:** Build scored from `review`, not `routed`.

## "Why did that fix work?" probes

**B1**
- Why did T04's decision and its place in r02's worklist not change?
- Where else in the code is a None confidence handled, and does it use the safe form?

**B2**
- Why did no item flip from auto_accept to human_review?
- Which data row would have made this bug change a decision?

**B3**
- Why were r02, r03, r06 and r07 unaffected?
- The comment says 'priority 1 is the most urgent'. Why didn't the code match it?

**B4**
- Why does the order of the two sort calls matter?
- Why did no other worklist change?

**B5**
- Why does routing in the report still print 'auto_accept'?
- Would `class Decision(str, Enum)` have hidden this? Is that a good fix?

**B6**
- Why is review_load right although it is built in the same function?
- Why must None be filtered out rather than counted as 0?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `hitlroute/assign.py` → `assign_reviewers`: It walks review items in item id order, filters to active reviewers with the skill and spare capacity (`load < capacity`), and picks min by (load, reviewer_id). That is exactly the README rule, and loads are shared across tasks as specified. The three toxicity items in the backlog are real: r01, r02 and r05 are full by then.
- `hitlroute/loader.py` → `parse_confidence`: Blank becomes None, '91%' becomes 0.91, and '0' becomes 0.0. `if not text` tests the string before conversion, so a zero confidence is not lost here.

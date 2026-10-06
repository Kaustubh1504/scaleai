# set-098 interviewer notes

**Scenario:** Votes for three moderation queues arrive from two vendors (CSV with ISO times, JSONL with Unix seconds). They are screened per vendor, deduped to each annotator's latest answer across vendors, and resolved by tier-weighted vote with expert tie-break and per-item deadlines. Test 3 checks the quality queue's annotator agreement and contested list.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Rejection dict as a mutable default

1. **Nudge:** Vendor A's rejections include b-10xx ids. How can vendor B's votes get into vendor A's dict?
2. **Area:** Look at where screen() gets the dict it writes rejections into.
3. **Exact:** Default `rejected=None` and create `rejected = {} if rejected is None else rejected` inside the function.

### B2: Vendor B seconds treated as milliseconds

1. **Nudge:** a03 answered S03 through both vendors. Which one was actually later?
2. **Area:** Print a vendor B vote's submitted_at.
3. **Exact:** from_epoch divides by 1000; the field is already in seconds, so pass it straight to fromtimestamp.

### B3: Tier compared with a string

1. **Nudge:** T02's weights are tied. Which tie-break rule should decide it?
2. **Area:** pick_label is VERIFIED. Check the expert counts it is given.
3. **Exact:** expert_votes compares tier with "expert"; compare with `is Tier.EXPERT`.

### B4: Vote at the deadline excluded

1. **Nudge:** S02 should have three counting votes. Which one is missing?
2. **Area:** Compare A-013's time with S02's closes_at.
3. **Exact:** within_window uses `<`; it should be `vote.submitted_at <= item.closes_at`.

### B5: Agreement counts escalated items

1. **Nudge:** a03 voted on Q03 and Q04 in the quality queue. Which of those should count?
2. **Area:** Look at which results annotator_agreement skips.
3. **Exact:** Skip anything whose status isn't 'accepted': `result.status != "accepted"`.

### B6: and/or precedence in contested filter

1. **Nudge:** Q03 isn't accepted. What lets it into the contested list?
2. **Area:** Read the boolean expression in contested() the way Python groups it.
3. **Exact:** Parenthesise: `r.status == "accepted" and (r.agreement < CONTESTED_BELOW or r.expert_dissent)`.

## "Why did that fix work?" probes

**B1**
- Why did the accepted votes stay correct while the rejection dicts were shared?
- Would the output have looked right if build_report only ever screened one vendor once?

**B2**
- Why did the S02 deadline not reject any vendor B votes while this was in place?
- What kind of test data would have made this change consensus results too?

**B3**
- Q03 is also a weight tie. Why was it unaffected?
- Would making Tier subclass str have hidden this? Is that a good fix?

**B4**
- Why was A-015 excluded either way?
- Name two other places in this report that silently depend on within_window.

**B5**
- Why did a02 and a08 keep the same score even though Q03 was being counted?
- Why is it risky to use 'label is not None' as a stand-in for 'decided'?

**B6**
- Why didn't pending items with no agreement crash the comparison?
- Which other queue's contested list also changed, and why didn't any test catch it?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `quorum/voting.py` → `pick_label`: min() over a negated key looks inverted, but (-weight, -expert votes, label) sorts the heaviest label first, then the one with the most expert votes, then alphabetical: exactly rule 9. The T02 symptom comes from the expert counts passed in, not from this function.
- `quorum/timeutil.py` → `parse_timestamp`: Stripping the trailing 'Z' and parsing naively looks lossy, but every vendor A and item time is UTC per the README, and from_epoch also returns naive UTC, so the two compare correctly.

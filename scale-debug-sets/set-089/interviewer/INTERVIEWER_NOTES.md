# set-089 interviewer notes

**Scenario:** Keep each active team's best result per active benchmark inside an end-exclusive contest window, normalise against the benchmark leader into a weighted composite, and rank with an earliest-finisher tie-break. The report counts distinct entrants per benchmark.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Submission at the window end counted

1. **Nudge:** orca's reasoning best is 52. Which submission is that, and when was it made?
2. **Area:** Compare that time with contest.json and the window rule in the README.
3. **Exact:** in_window should be `start <= ts < end`.

### B2: Tie-break uses first submission time

1. **Nudge:** Which two teams swapped places? Compare their composites.
2. **Area:** The sort key in ranking.py looks right. Where do its time values come from?
3. **Exact:** team_bests builds last_seen with min(ts); rule 9 needs max(ts).

### B3: Entrant count counts submissions, not teams

1. **Nudge:** reasoning and latency_ms are one too high; coding and safety are fine. What is different about those two benchmarks?
2. **Area:** Look at how benchmark_stats gathers entrants.
3. **Exact:** Collect teams in a set (defaultdict(set) / .add) so each team counts once.

## "Why did that fix work?" probes

**B1**
- Why did the standings test still pass with this bug?
- S35 is exactly at `start`. Why must it stay in?

**B2**
- Why is ranking.py, the file that does the sorting, not where the fix goes?
- Why can't the team id ever decide the order in this data?

**B3**
- Narwhal's S07 appears twice in the CSV. Why didn't it inflate the count too?
- Why do coding and safety come out right even with this bug?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `evalboard/loader.py` → `parse_time`: It tries exactly the three formats the README lists, with month/day order for the slash format, and raises on anything else. The `continue` inside `except` only moves on to the next format.
- `evalboard/scoring.py` → `normalise`: For a lower-is-better benchmark the leader has the smallest value, so `best / score` puts the leader at 1.0 and every slower team below 1. It looks inverted, but it is exactly spec rule 6.

# set-087 interviewer notes

**Scenario:** Normalise vendor chat logs (role aliases, late system turns, merged turns), render them into a chat template and trim the oldest pairs to a per-source token budget. The report counts tags over kept examples.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Late system turn ends the conversation

1. **Nudge:** c06 has 4 user/assistant turns in the data but only one pair in the output, and dropped_pairs is 0. So truncation did not remove it. What did?
2. **Area:** Follow c06 through normalise_turns. What happens when it reaches the second system turn?
3. **Exact:** `break` should be `continue` in the late-system-turn check in normalise_turns.

### B2: Example exactly at budget gets trimmed

1. **Nudge:** Count c09's tokens by hand and compare with vendor-b's budget in sources.csv.
2. **Area:** Look at the loop condition that decides whether to drop another pair.
3. **Exact:** fit_budget uses `total >= budget`; the spec says at-or-under fits, so it should be `total > budget`.

### B3: Blank tag pieces counted as a tag

1. **Nudge:** tag_counts has a key that is an empty string. Which conversations could produce it?
2. **Area:** Look at how the tags string is split in the loader.
3. **Exact:** parse_tags needs to drop empty pieces: `return [p for p in parts if p]`.

## "Why did that fix work?" probes

**B1**
- dropped_pairs was 0. Why was that the key clue that fit_budget was not involved?
- Which data shape would make `break` and `continue` give the same output here?

**B2**
- vendor-b's max_tokens cell is blank. Where does 64 come from, and could that blank have been the cause instead?
- Why didn't c04 change with this bug, even though it is also trimmed?

**B3**
- Which three conversations contributed to the empty-string count? Why not c10, which also has blank tags?
- Would `clean(raw).split()` have been a valid fix? Why or why not?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `chatpack/budget.py` → `count_tokens`: `str.split()` with no argument splits on runs of whitespace and returns [] for an empty string, so it counts words correctly, including the `\n` that merged turns contain. Candidates who just saw the tag `split(';')` issue often suspect this too.
- `chatpack/formatting.py` → `merge_consecutive`: It replaces merged[-1] with a new frozen Turn instead of mutating a shared object, and joins contents with `\n` exactly as the spec says. It runs after late system turns are removed, so two user turns separated by a dropped system turn are merged, which is what the spec order implies.

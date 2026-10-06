# set-072 interviewer notes

**Scenario:** Clean a speech-clip export (consent, duration, per-speaker duplicate transcripts), then assign whole speakers to train/val/test per accent stratum by seeded sha256 order, with held-out speakers forced into test. Test 3 checks the validation split's minutes and accent mix.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Consent flag read with bool()

1. **Nudge:** Which clips are still listed as no_consent, and what do their consent cells say?
2. **Area:** Look at how consent strings become booleans.
3. **Exact:** parse_flag returns bool(clean(value)); it should be clean(value).lower() in TRUTHY.

### B2: Clip of exactly max duration rejected

1. **Nudge:** C004 is in the duration list. How long is it, and what is the configured max?
2. **Area:** Check the duration comparison in filters.py against README rule 4.
3. **Exact:** Use `<= config["max_ms"]` on the upper bound.

### B3: Held-out removal skips the next speaker

1. **Nudge:** S09 is marked held-out but ended in train. Which other held-out speaker is next to it in the uk stratum?
2. **Area:** Look at how take_held_out walks the pool while removing from it.
3. **Exact:** Iterate over a copy: `for spk in list(pool):`.

### B4: Accent not lower-cased

1. **Nudge:** Where does the 'US' key in strata come from?
2. **Area:** Compare how accents and ids are normalised in loader.py.
3. **Exact:** Use norm_code(row["accent"]) for the accent.

### B5: Minutes floored to whole minutes

1. **Nudge:** The val split has about 100 seconds of audio. Why would minutes be a whole number?
2. **Area:** Look at how minutes() converts milliseconds.
3. **Exact:** Use true division: total_ms / 60_000.

### B6: Accent mix counts letters

1. **Nudge:** The accents map has single-letter keys. Where could letters come from?
2. **Area:** Look at how accent_mix adds to its Counter.
3. **Exact:** Use mix[accent] += 1 (or update([accent])).

## "Why did that fix work?" probes

**B1**
- Why did the held_out column survive this helper unchanged?
- Why didn't these extra clips change any speaker's split?

**B2**
- Why is C002 (also 30000 ms) not in the duration list?
- Why did C026 (exactly 1000 ms) pass even with this bug?

**B3**
- Why was S19, also held-out, handled correctly?
- Why did no regular speaker change split when S09 leaked into the pool?

**B4**
- S04 still ended up in train. Why did that happen with the bug, and would it always?
- Why did ' uk' (S05) and 'us ' (S16) behave correctly anyway?

**B5**
- Why didn't the round(..., 2) protect against this?
- Which split totals would a test have to check to catch this with other data?

**B6**
- Why does strata_sizes, which also uses Counter, give accent keys?
- What would update([accent]) do differently?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `voxsplit/normalize.py` → `parse_recorded`: `%d/%m/%Y` looks like a US-format slip, but the spec says the slash format is day/month/year (London studio). This matters for duplicates: C006 (26/04) is earlier than C005 (2026-04-27).
- `voxsplit/hashing.py` → `hash_order`: Sorting by the hex digest string looks like it should convert to an int first, but every sha256 hex digest is 64 lower-case characters, so lexicographic order equals numeric order. The spec orders by the hex digest.

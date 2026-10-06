# set-072 answer key: Speaker-disjoint, accent-stratified speech splits

**Domain:** dataset_split  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_cleaning.TestCleaning.test_consent_exclusions` | B1 Consent flag read with bool() |
| `test_1_cleaning.TestCleaning.test_duration_exclusions` | B2 Clip of exactly max duration rejected |
| `test_2_assignment.TestAssignment.test_held_out_speakers_in_test` | B3 Held-out removal skips the next speaker |
| `test_2_assignment.TestAssignment.test_strata_sizes` | B4 Accent not lower-cased |
| `test_3_report.TestValidationSplit.test_val_minutes` | B5 Minutes floored to whole minutes |
| `test_3_report.TestValidationSplit.test_val_accent_mix` | B6 Accent mix counts letters |

## Failing pattern with all bugs present

- `tests.test_1_cleaning.TestCleaning.test_consent_exclusions`
- `tests.test_1_cleaning.TestCleaning.test_duration_exclusions`
- `tests.test_2_assignment.TestAssignment.test_held_out_speakers_in_test`
- `tests.test_2_assignment.TestAssignment.test_strata_sizes`
- `tests.test_3_report.TestValidationSplit.test_val_accent_mix`
- `tests.test_3_report.TestValidationSplit.test_val_minutes`

## Bugs (recommended order)

### B1: Consent flag read with bool()

- **Type:** bool-from-string
- **Symptom:** Test 1 test_consent_exclusions: only ['C027'] (the blank cell) is listed as no_consent; C002 ('no'), C012 ('false') and C017 ('0') are missing. Nothing else fails because those clips belong to train speakers who have other clips.
- **Location:** `voxsplit/normalize.py` → `parse_flag`
- **Why it fails:** bool() of any non-empty string is True, so 'no', 'false' and '0' all count as consent. Only the blank cell stays false. held_out goes through the same helper but only uses yes/Y/TRUE/blank, so it is unaffected.
- **Failing test:** `test_1_cleaning.TestCleaning.test_consent_exclusions`
- **Unblocks:** test_consent_exclusions.

Fix:

```diff
-    return bool(clean(value))
+    return clean(value).lower() in TRUTHY
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_consent_exclusions`):

```
AssertionError: Lists differ: ['C027'] != ['C002', 'C012', 'C017', 'C027']

First differing element 0:
'C027'
'C002'

Second list contains 3 additional elements.
First extra element 1:
'C012'

- ['C027']
+ ['C002', 'C012', 'C017', 'C027']
```

### B2: Clip of exactly max duration rejected

- **Type:** off-by-one
- **Symptom:** Test 1 test_duration_exclusions: the list is ['C004', 'C011', 'C022']; C004 is exactly 30000 ms, the configured max.
- **Location:** `voxsplit/filters.py` → `exclusion_reason`
- **Why it fails:** The spec allows both limits. With `<` on the upper bound, C004 (exactly 30000 ms) is excluded as `duration`.
- **Failing test:** `test_1_cleaning.TestCleaning.test_duration_exclusions`
- **Unblocks:** test_duration_exclusions.

Fix:

```diff
-    if not config["min_ms"] <= clip.duration_ms < config["max_ms"]:
+    if not config["min_ms"] <= clip.duration_ms <= config["max_ms"]:
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_duration_exclusions`):

```
AssertionError: Lists differ: ['C004', 'C011', 'C022'] != ['C011', 'C022']

First differing element 0:
'C004'
'C011'

First list contains 1 additional elements.
First extra element 2:
'C022'

- ['C004', 'C011', 'C022']
?  --------

+ ['C011', 'C022']
```

### B3: Held-out removal skips the next speaker

- **Type:** mutate-while-iterating
- **Symptom:** Test 2 test_held_out_speakers_in_test: S09 is assigned 'train' instead of 'test'. The regular speakers keep their splits.
- **Location:** `voxsplit/stratify.py` → `take_held_out`
- **Why it fails:** Removing S08 from the list being iterated shifts S09 into the slot the iterator has already passed, so S09 is never seen. It stays in the pool and is allocated by hash order, landing in train.
- **Failing test:** `test_2_assignment.TestAssignment.test_held_out_speakers_in_test`
- **Unblocks:** test_held_out_speakers_in_test.

Fix:

```diff
-    for spk in pool:
+    for spk in list(pool):
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_held_out_speakers_in_test`):

```
AssertionError: {'S08': 'test', 'S09': 'train', 'S19': 'test'} != {'S08': 'test', 'S09': 'test', 'S19': 'test'}
- {'S08': 'test', 'S09': 'train', 'S19': 'test'}
?                          ^^^^

+ {'S08': 'test', 'S09': 'test', 'S19': 'test'}
?                          ^^^
```

### B4: Accent not lower-cased

- **Type:** id-normalization
- **Symptom:** Test 2 test_strata_sizes: strata is {'US': 1, 'au': 3, 'in': 4, 'uk': 7, 'us': 6} instead of four lower-case strata.
- **Location:** `voxsplit/loader.py` → `load_speakers`
- **Why it fails:** S04's accent is 'US'. Without lower-casing it forms its own one-speaker stratum, so the strata (and the stratified allocation) no longer follow the spec.
- **Failing test:** `test_2_assignment.TestAssignment.test_strata_sizes`
- **Unblocks:** test_strata_sizes.

Fix:

```diff
-accent=clean(row["accent"])
+accent=norm_code(row["accent"])
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_strata_sizes`):

```
AssertionError: {'US': 1, 'au': 3, 'in': 4, 'uk': 7, 'us': 6} != {'au': 3, 'in': 4, 'uk': 7, 'us': 7}
- {'US': 1, 'au': 3, 'in': 4, 'uk': 7, 'us': 6}
?  ---------                                 ^

+ {'au': 3, 'in': 4, 'uk': 7, 'us': 7}
?                                   ^
```

### B5: Minutes floored to whole minutes

- **Type:** integer-division
- **Symptom:** Test 3 test_val_minutes: 1 instead of 1.66.
- **Location:** `voxsplit/reports.py` → `minutes`
- **Why it fails:** `//` floors before rounding, so 99 550 ms becomes 1 minute instead of 1.66. round(..., 2) of an int changes nothing.
- **Failing test:** `test_3_report.TestValidationSplit.test_val_minutes`
- **Unblocks:** test_val_minutes.

Fix:

```diff
-    return round(total_ms // 60_000, 2)
+    return round(total_ms / 60_000, 2)
```

Observed with only this bug applied (`tests.test_3_report.TestValidationSplit.test_val_minutes`):

```
AssertionError: 1 != 1.66
```

### B6: Accent mix counts letters

- **Type:** counter-misuse
- **Symptom:** Test 3 test_val_accent_mix: {'i': 2, 'k': 2, 'n': 2, 's': 3, 'u': 5} instead of {'in': 2, 'uk': 2, 'us': 3}.
- **Location:** `voxsplit/stats.py` → `accent_mix`
- **Why it fails:** Counter.update() with a string iterates it, so each clip adds one count per character ('u', 's', 'k', 'i', 'n') instead of one count for the accent.
- **Failing test:** `test_3_report.TestValidationSplit.test_val_accent_mix`
- **Unblocks:** test_val_accent_mix.

Fix:

```diff
-        mix.update(speakers[clip.speaker_id].accent)
+        mix[speakers[clip.speaker_id].accent] += 1
```

Observed with only this bug applied (`tests.test_3_report.TestValidationSplit.test_val_accent_mix`):

```
AssertionError: {'i': 2, 'k': 2, 'n': 2, 's': 3, 'u': 5} != {'in': 2, 'uk': 2, 'us': 3}
- {'i': 2, 'k': 2, 'n': 2, 's': 3, 'u': 5}
+ {'in': 2, 'uk': 2, 'us': 3}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `voxsplit/normalize.py` → `parse_recorded`: `%d/%m/%Y` looks like a US-format slip, but the spec says the slash format is day/month/year (London studio). This matters for duplicates: C006 (26/04) is earlier than C005 (2026-04-27).
- `voxsplit/hashing.py` → `hash_order`: Sorting by the hex digest string looks like it should convert to an int first, but every sha256 hex digest is 64 lower-case characters, so lexicographic order equals numeric order. The spec orders by the hex digest.

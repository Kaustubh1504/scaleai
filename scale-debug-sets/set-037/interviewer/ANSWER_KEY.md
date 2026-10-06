# set-037 answer key: Card fraud screen: velocity, unknown currencies, rejects

**Domain:** fraud_detection  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_scoring.TestScoring.test_velocity_window` | B1 Velocity window drops the transaction exactly 10 minutes old |
| `test_1_scoring.TestScoring.test_unknown_currency` | B2 Unknown-currency transactions silently skipped |
| `test_2_report.TestReport.test_rejected_rows` | B3 ValueError handler catches missing fields first |

## Failing pattern with all bugs present

- `tests.test_1_scoring.TestScoring.test_unknown_currency`
- `tests.test_1_scoring.TestScoring.test_velocity_window`
- `tests.test_2_report.TestReport.test_rejected_rows`

## Bugs (recommended order)

### B1: Velocity window drops the transaction exactly 10 minutes old

- **Type:** time-window-boundary
- **Symptom:** Test 1 test_velocity_window: T006 comes out ([], "allow") instead of (["velocity"], "review"). The c03 burst (all within 5 minutes) is still flagged.
- **Location:** `fraudlens/rules.py` → `velocity_hit`
- **Why it fails:** T002 is at 09:00:00 and T006 at 09:10:00, exactly 10 minutes apart. The README keeps that inside the window, but >= evicts T002 before counting, so T006 sees only 2 transactions.
- **Failing test:** `test_1_scoring.TestScoring.test_velocity_window`
- **Unblocks:** Test 1 test_velocity_window.

Fix:

```diff
-    while state.recent and ts - state.recent[0] >= VELOCITY_WINDOW:
+    while state.recent and ts - state.recent[0] > VELOCITY_WINDOW:
```

Observed with only this bug applied (`tests.test_1_scoring.TestScoring.test_velocity_window`):

```
AssertionError: {'T00[35 chars]low'), 'T006': ([], 'allow'), 'T028': ([], 'allow')} != {'T00[35 chars]low'), 'T006': (['velocity'], 'review'), 'T028': ([], 'allow')}
  {'T002': ([], 'allow'),
   'T003': ([], 'allow'),
-  'T006': ([], 'allow'),
+  'T006': (['velocity'], 'review'),
   'T028': ([], 'allow')}
```

### B2: Unknown-currency transactions silently skipped

- **Type:** swallowed-exception
- **Symptom:** Test 1 test_unknown_currency: card c05 has no decision for T011 at all (only T009 and T023). The summary still says 25 loaded, so a transaction silently has no decision.
- **Location:** `fraudlens/engine.py` → `score_all`
- **Why it fails:** The handler catches UnknownCurrencyError and just continues, so T011 (ZAR) never gets a decision. The README wants it sent to review with an unknown_currency flag. Nothing else changes because the exception is raised before any card state is updated.
- **Failing test:** `test_1_scoring.TestScoring.test_unknown_currency`
- **Unblocks:** Test 1 test_unknown_currency.

Fix:

```diff
-        except UnknownCurrencyError:
+        except UnknownCurrencyError as exc:
+            decisions[txn.txn_id] = Decision(txn.txn_id, txn.card_id, None, UNKNOWN_CURRENCY_SCORE,
+                                             [f"unknown_currency:{exc.currency}"], "review")
```

Observed with only this bug applied (`tests.test_1_scoring.TestScoring.test_unknown_currency`):

```
AssertionError: {'T00[17 chars], 'T023': (['foreign'], 'allow')} != {'T00[17 chars], 'T011': (['unknown_currency:ZAR'], 'review')[28 chars]ow')}
- {'T009': ([], 'allow'), 'T023': (['foreign'], 'allow')}
+ {'T009': ([], 'allow'),
+  'T011': (['unknown_currency:ZAR'], 'review'),
+  'T023': (['foreign'], 'allow')}
```

### B3: ValueError handler catches missing fields first

- **Type:** exception-order
- **Symptom:** Test 2 test_rejected_rows: T015, T021 and T029 have reason "unparseable" instead of missing:card_id / missing:amount. The rejected count (5) is unchanged.
- **Location:** `fraudlens/loader.py` → `load_transactions`
- **Why it fails:** MissingFieldError subclasses ValueError, and except clauses are tried top to bottom. With ValueError first, every missing field is reported as unparseable and the MissingFieldError branch can never run.
- **Failing test:** `test_2_report.TestReport.test_rejected_rows`
- **Unblocks:** Test 2 test_rejected_rows.

Fix:

```diff
+            except MissingFieldError as exc:
+                rejected.append({"txn_id": txn_id, "reason": f"missing:{exc.field}"})
             except ValueError:
                 rejected.append({"txn_id": txn_id, "reason": "unparseable"})
-            except MissingFieldError as exc:
-                rejected.append({"txn_id": txn_id, "reason": f"missing:{exc.field}"})
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_rejected_rows`):

```
AssertionError: Lists differ: [{'tx[21 chars]n': 'unparseable'}, {'txn_id': 'T021', 'reason[148 chars]le'}] != [{'tx[21 chars]n': 'missing:card_id'}, {'txn_id': 'T021', 're[158 chars]nt'}]

First differing element 0:
{'txn_id': 'T015', 'reason': 'unparseable'}
{'txn_id': 'T015', 'reason': 'missing:card_id'}

- [{'reason': 'unparseable', 'txn_id': 'T015'},
?              ^ ^  ^^^^^^

+ [{'reason':  ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `fraudlens/money.py` → `parse_amount`: Stripping every comma looks like it could break decimal commas, but the README says commas are thousands separators. '1,050.00' -> 1050.0 and '12,000' -> 12000.0 are both right; '12.5O' still raises ValueError, which is what makes T024 unparseable.

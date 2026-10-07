# set-030 answer key: Support ticket workflow replay with a data-driven transition table

**Domain:** review_state_machine  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_replay.TestReplay.test_lead_resolution` | B1 First matching transition ends the search |
| `test_1_replay.TestReplay.test_agent_handoff` | B2 People ids keep their original case |
| `test_2_tickets.TestTickets.test_labels` | B3 Ticket defaults copied shallowly |
| `test_2_tickets.TestTickets.test_first_response_after_triage` | B4 Text flag read with bool() |
| `test_3_report.TestReport.test_sla_breaches` | B5 Responding at the limit counted as a breach |
| `test_3_report.TestReport.test_actor_activity` | B6 Counter updated with a string |

## Failing pattern with all bugs present

- `tests.test_1_replay.TestReplay.test_agent_handoff`
- `tests.test_1_replay.TestReplay.test_lead_resolution`
- `tests.test_2_tickets.TestTickets.test_first_response_after_triage`
- `tests.test_2_tickets.TestTickets.test_labels`
- `tests.test_3_report.TestReport.test_actor_activity`
- `tests.test_3_report.TestReport.test_sla_breaches`

## Bugs (recommended order)

### B1: First matching transition ends the search

- **Type:** early-return
- **Symptom:** Test 1 test_lead_resolution: T03 ends as ('in_progress', 10:10) instead of ('closed', 11:30); lee's 10:40 resolve is refused (role_not_allowed) and the 11:30 close is then refused too.
- **Location:** `ticketflow/workflow.py` → `find_transition`
- **Why it fails:** The table has two in_progress/resolve entries: the agent one first, the lead one second. Returning None as soon as the first (state, action) match refuses the actor never reaches the lead's entry, so lee's resolve on T03 is refused as role_not_allowed and the following close is then invalid.
- **Failing test:** `test_1_replay.TestReplay.test_lead_resolution`
- **Unblocks:** test_lead_resolution.

Fix:

```diff
         if t.source == state and t.action == action:
-            return t if role in t.roles else None
+            if role in t.roles:
+                return t
```

Observed with only this bug applied (`tests.test_1_replay.TestReplay.test_lead_resolution`):

```
AssertionError: Tuples differ: ('in_progress', datetime.datetime(2026, 5, 4, 10, 10)) != ('closed', datetime.datetime(2026, 5, 4, 11, 30))

First differing element 0:
'in_progress'
'closed'

- ('in_progress', datetime.datetime(2026, 5, 4, 10, 10))
?   ^^^^^ ^^ ^^                                  ^  ^

+ ('closed', datetime.datetime(2026, 5, 4, 11, 30))
?   ^^ ^ ^                                  ^ ...
```

### B2: People ids keep their original case

- **Type:** id-normalization
- **Symptom:** Test 1 test_agent_handoff: T09 stays ('new', None) instead of ('resolved', 13:30); every T09 event is refused, starting with noor's triage.
- **Location:** `ticketflow/loader.py` → `load_people`
- **Why it fails:** people.json lists Noor with a capital N while event actors are lower-cased, so the lookup for 'noor' finds no role. Her triage is refused (role_not_allowed) and every later step on T09 is invalid from state new.
- **Failing test:** `test_1_replay.TestReplay.test_agent_handoff`
- **Unblocks:** test_agent_handoff.

Fix:

```diff
-        return {clean(p["id"]): clean(p["role"]).lower() for p in json.load(fh)}
+        return {clean(p["id"]).lower(): clean(p["role"]).lower() for p in json.load(fh)}
```

Observed with only this bug applied (`tests.test_1_replay.TestReplay.test_agent_handoff`):

```
AssertionError: Tuples differ: ('new', None) != ('resolved', datetime.datetime(2026, 5, 4, 13, 30))

First differing element 0:
'new'
'resolved'

- ('new', None)
+ ('resolved', datetime.datetime(2026, 5, 4, 13, 30))
```

### B3: Ticket defaults copied shallowly

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 2 test_labels: every ticket (T01, T02, T06 and the never-tagged T10) reports ['billing', 'login', 'outage'].
- **Location:** `ticketflow/models.py` → `new_ticket`
- **Why it fails:** A shallow copy of the defaults dict still shares the one `labels` list, so every ticket appends to the same list and each ticket reports every tag in the log.
- **Failing test:** `test_2_tickets.TestTickets.test_labels`
- **Unblocks:** test_labels.

Fix:

```diff
-    fields = copy.copy(TICKET_DEFAULTS)
+    fields = copy.deepcopy(TICKET_DEFAULTS)
```

Observed with only this bug applied (`tests.test_2_tickets.TestTickets.test_labels`):

```
AssertionError: {'T01': ['billing', 'login', 'outage'], 'T02': ['billing', [92 chars]ge']} != {'T01': ['billing'], 'T02': ['login'], 'T06': ['outage'], 'T10': []}
+ {'T01': ['billing'], 'T02': ['login'], 'T06': ['outage'], 'T10': []}
- {'T01': ['billing', 'login', 'outage'],
-  'T02': ['billing', 'login', 'outage'],
-  'T06': ['billing', 'login', 'outage'],
-  'T10': ['billing', 'login', 'outage'] ...
```

### B4: Text flag read with bool()

- **Type:** bool-from-string
- **Symptom:** Test 2 test_first_response_after_triage: T02 10.0, T04 20.0, T12 30.0, T14 10.0 instead of 55.0, None, 180.0, 30.0. The triage time is counted as the first response.
- **Location:** `ticketflow/workflow.py` → `load_workflow`
- **Why it fails:** The triage entry stores counts_as_response as the text "false", and bool() of any non-empty string is True. Triage then sets the first response, so triaged tickets report their triage time instead of the first reply.
- **Failing test:** `test_2_tickets.TestTickets.test_first_response_after_triage`
- **Unblocks:** test_first_response_after_triage.

Fix:

```diff
# ticketflow/workflow.py
-            counts_as_response=bool(item.get("counts_as_response", False)),
+            counts_as_response=parse_flag(item.get("counts_as_response", False)),

# ticketflow/workflow.py
-from .loader import clean
+from .loader import clean, parse_flag
```

Observed with only this bug applied (`tests.test_2_tickets.TestTickets.test_first_response_after_triage`):

```
AssertionError: {'T02': 10.0, 'T04': 20.0, 'T12': 30.0, 'T14': 10.0} != {'T02': 55.0, 'T04': None, 'T12': 180.0, 'T14': 30.0}
- {'T02': 10.0, 'T04': 20.0, 'T12': 30.0, 'T14': 10.0}
?         ^^           ^^^^         ^            ^

+ {'T02': 55.0, 'T04': None, 'T12': 180.0, 'T14': 30.0}
?         ^^           ^^^^         ^^            ^
```

### B5: Responding at the limit counted as a breach

- **Type:** time-window-boundary
- **Symptom:** Test 3 test_sla_breaches: the list is ['T05', 'T07', 'T11', 'T13']. T11, answered after exactly 120 minutes, is added.
- **Location:** `ticketflow/sla.py` → `breached`
- **Why it fails:** The README says a response exactly at the limit is on time. T11 (severity 2, 120 minutes) was answered after exactly 120 minutes, and >= marks it as breached.
- **Failing test:** `test_3_report.TestReport.test_sla_breaches`
- **Unblocks:** test_sla_breaches.

Fix:

```diff
-    return waited >= sla_minutes(ticket)
+    return waited > sla_minutes(ticket)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_sla_breaches`):

```
AssertionError: Lists differ: ['T05', 'T07', 'T11', 'T13'] != ['T05', 'T07', 'T13']

First differing element 2:
'T11'
'T13'

First list contains 1 additional elements.
First extra element 3:
'T13'

- ['T05', 'T07', 'T11', 'T13']
?                -------

+ ['T05', 'T07', 'T13']
```

### B6: Counter updated with a string

- **Type:** counter-misuse
- **Symptom:** Test 3 test_actor_activity: actors are right but the inner counts are keyed by single characters, e.g. acme -> {'_': 2, 'c': 2, 'e': 4, ...} instead of {'customer_reply': 2}.
- **Location:** `ticketflow/reports.py` → `actor_activity`
- **Why it fails:** Counter.update with a string iterates it, so each action adds one count per character ('r', 'e', 'p', ...) instead of one count for the action name.
- **Failing test:** `test_3_report.TestReport.test_actor_activity`
- **Unblocks:** test_actor_activity.

Fix:

```diff
-        stats[event.actor].update(event.action)
+        stats[event.actor][event.action] += 1
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_actor_activity`):

```
AssertionError: {'acme': {'_': 2, 'c': 2, 'e': 4, 'l': 2, 'm': 2, 'o[789 chars]: 1}} != {'acme': {'customer_reply': 2}, 'ana': {'reply': 5, [341 chars]: 1}}
Diff is 2037 characters long. Set self.maxDiff to None to see it.
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `ticketflow/engine.py` → `ordered`: Sorting on (ts, seq) is exactly the README rule: timestamp order, seq breaking ties. It matters for T10, where the customer_reply and the resolve share 14:50 and appear in the file in reverse order.
- `ticketflow/loader.py` → `parse_flag`: Text is true only for true/yes/y/1 after trimming and lower-casing; real JSON booleans go through bool(), which is right for them. The bool() fallback looks suspicious but only applies to non-strings.

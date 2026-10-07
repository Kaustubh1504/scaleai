# set-030 interviewer notes

**Scenario:** Replay an unordered support-desk event log through a transition table loaded from workflow.json (roles per transition, an agent resolve that needs lead approval vs a lead's final resolve), then report ticket states, labels, first-response times, response-SLA breaches (severity 1 is most urgent, VIP halves the limit) and per-actor activity. Test 3 is the report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: First matching transition ends the search

1. **Nudge:** Only the lead's resolve is refused; agents resolve fine. What is different about the lead's entry in workflow.json?
2. **Area:** Look at how find_transition walks entries that share a state and action.
3. **Exact:** Keep looping when the role isn't in t.roles; return None only after the loop.

### B2: People ids keep their original case

1. **Nudge:** Every action on T09 is refused, starting with noor's triage. What role does the replay think she has?
2. **Area:** Compare how person ids are normalised in load_people and in load_events.
3. **Exact:** Lower-case the id key in load_people.

### B3: Ticket defaults copied shallowly

1. **Nudge:** Every ticket shows the same labels, even T10, which was never tagged.
2. **Area:** Where does each Ticket get its labels list from?
3. **Exact:** Use copy.deepcopy (or build a fresh list) in new_ticket.

### B4: Text flag read with bool()

1. **Nudge:** Only tickets that were triaged before their first reply are off. Which event became their first response?
2. **Area:** Check how counts_as_response is read in load_workflow and what the triage entry holds.
3. **Exact:** Use parse_flag for counts_as_response.

### B5: Responding at the limit counted as a breach

1. **Nudge:** One extra ticket is listed. How long did it wait, and what is its limit?
2. **Area:** Read the breach rule in the README and compare it with breached().
3. **Exact:** Use a strict > comparison.

### B6: Counter updated with a string

1. **Nudge:** The actor keys are right, but the inner keys are single letters.
2. **Area:** What does Counter.update do when it is given a str?
3. **Exact:** Increment stats[event.actor][event.action] by 1 (or update with [event.action]).

## "Why did that fix work?" probes

**B1**
- Why does the order of the two resolve entries in workflow.json matter for this symptom?
- Why is the refusal reason role_not_allowed rather than invalid_transition?

**B2**
- Why do the other people.json entries with stray spaces still work?
- Why are the later T09 events refused as invalid_transition and not role_not_allowed?

**B3**
- Why does the dedupe check in Replay.apply make the shared list look tidy rather than full of repeats?
- Why are state and first_response unaffected by the same copy?

**B4**
- Why does the customer_reply entry ("no") not change any result even with bool()?
- Why are none of the SLA breaches affected?

**B5**
- Why is T07, which never got a response, breached either way?
- What other data would expose a VIP boundary case?

**B6**
- Why are the actor names themselves still right?
- How would you write the same count with Counter over (actor, action) pairs?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `ticketflow/engine.py` → `ordered`: Sorting on (ts, seq) is exactly the README rule: timestamp order, seq breaking ties. It matters for T10, where the customer_reply and the resolve share 14:50 and appear in the file in reverse order.
- `ticketflow/loader.py` → `parse_flag`: Text is true only for true/yes/y/1 after trimming and lower-casing; real JSON booleans go through bool(), which is right for them. The bool() fallback looks suspicious but only applies to non-strings.

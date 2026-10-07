# set-030 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. How does build_report run the replay?

It loads tickets.csv into Ticket objects keyed by upper-cased id, people.json into an id -> role dict, workflow.json into a list of Transition objects, and events.csv into Event objects. It then builds a Replay and calls run(events), which applies events in ordered() order, and builds each report section from the tickets, replay.rejected and the raw events.

### 2. What does Replay.apply do with a non-tag event?

It looks up the actor's role in the people dict (None if missing), asks find_transition for an entry matching the ticket's state, the action and the role, and if there is none uses has_transition to choose between role_not_allowed and invalid_transition. On success it sets state and updated_at, and sets first_response if the transition counts_as_response and the ticket has none yet.

### 3. What does find_transition return?

A Transition from the list, scanned in workflow.json file order, whose source and action match and whose roles contain the role; otherwise None. has_transition only checks source and action.

### 4. Where does each ticket's labels list come from?

new_ticket in models.py copies the module-level TICKET_DEFAULTS dict (state 'new', labels, first_response None, updated_at None) and passes the copy's values into the Ticket dataclass. Replay.apply appends tag values to ticket.labels if they aren't already there.

### 5. How are counts_as_response values read from workflow.json?

load_workflow builds one Transition per entry, cleaning and lower-casing from/action/to/roles and converting counts_as_response with the expression in the Transition(...) call; a missing key defaults to False. In the data the value appears both as JSON booleans and as text such as "false", "yes" and "no".

### 6. How is an SLA breach decided?

sla_minutes looks up SLA_MINUTES by severity and halves it for VIP tickets. breached takes the first response (or as_of when there is none), computes the minutes since opened_at with total_seconds()/60, and compares that with the limit. breaches returns the sorted ids.

### 7. What does actor_activity count?

It walks every loaded event (accepted or refused) and keeps a Counter per actor in a defaultdict, then returns {actor: {key: count}} with both levels sorted.

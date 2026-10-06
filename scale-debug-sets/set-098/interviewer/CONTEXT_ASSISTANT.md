# set-098 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the pipeline inside build_report?

Load annotators, config (weights, queues, aliases) and items. Read each vendor file and screen it separately with `screening.screen`. Concatenate the kept votes (vendor A first) and pass them to `latest_only`, then to `voting.resolve`. Finally build one `queue_report` per queue name.

### 2. What does vendor B's reader do with the `submitted` field?

`read_vendor_b` passes `rec['submitted']` to `timeutil.from_epoch`, which builds a datetime with `datetime.fromtimestamp(..., tz=timezone.utc)` and strips the tzinfo so it can be compared with the naive datetimes from vendor A.

### 3. How does latest_only decide which vote is superseded?

It walks the combined list keyed by (item_id, annotator_id). A vote whose submitted_at is >= the stored one replaces it, and the stored vote's id goes to `superseded`. Otherwise the new vote's id is superseded. It returns the surviving votes and the sorted superseded ids.

### 4. How are ties between labels resolved in decide()?

decide builds `totals` (label → summed tier weight) and `experts` (label → `expert_votes(counted, annotators, label)`), then calls the VERIFIED `pick_label(totals, experts)`.

### 5. Which votes does decide() count?

Only the item's votes for which `within_window(vote, item)` is true. Items without closes_at accept everything. The count of those votes is compared with `item.min_votes` (from items.csv, or the queue default when blank).

### 6. What votes and results go into a queue's agreement table?

`queue_report` passes the queue's results and the deduped votes on its items that are within the item window. `annotator_agreement` then skips results according to its status/label check, and counts per annotator how many remaining votes match `result.label`.

### 7. Where does an Annotator's tier come from, and what type is it?

`registry.load_annotators` lower-cases the JSON `tier` string and converts it with `Tier(...)`, so it is a `models.Tier` Enum member (a plain Enum, not a str subclass). The weights dict in `load_config` is keyed by Tier members too.

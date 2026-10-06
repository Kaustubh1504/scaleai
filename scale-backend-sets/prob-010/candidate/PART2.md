# Part 2: Audit trail (about 20 minutes)

Some of these documents are contracts and identity documents; compliance must
be able to answer "who decided this label, when, and based on what?" for any
document. Record every change as an **audit event**. Everything from Part 1
still holds.

## Events

```json
{"seq": 17, "ts": 1700000005.0, "doc_id": "DOC-1006", "actor": "system",
 "action": "routed_to_review", "from_status": "ingested", "to_status": "needs_review",
 "details": {"review_reason": "low_confidence"}}
```

* `seq`: a positive integer, strictly increasing in the order events are
  appended, across all documents. Never reused, including after a restart.
* `ts`: the app clock's time (`clock.time()`) when the event was appended.
* `actor`: `"system"` for everything the service does on its own; the reviewer
  (stripped) for a review.
* Events are immutable: once appended, an event never changes and is never removed.

| action | appended when | `from_status` | `to_status` | `details` contains at least |
|---|---|---|---|---|
| `ingested` | a row is accepted by `POST /batches` | `null` | `ingested` | `batch_id` |
| `classified` | a classification finished (success or failure) | `ingested` | `ingested` | `label`, `confidence`, `attempts`, `error` (as in the document's `classification`) |
| `auto_accepted` | the document is auto-accepted | `ingested` | `auto_accepted` | `final_label`, `confidence` |
| `routed_to_review` | the document enters `needs_review` | `ingested` | `needs_review` | `review_reason` |
| `reviewed` | a review succeeds | `needs_review` | `reviewed` | `label` (the reviewer's), `model_label` (the classification's label, `null` if it failed) |

* Classifying a document appends `classified` followed by its routing event
  (`auto_accepted` or `routed_to_review`); nothing else is appended for that
  document in between.
* A request that fails (4xx) appends nothing. Rows rejected at upload have no events.
* A status change and its event are recorded together: there is never a status
  change without its event, or an event for a change that did not happen.

## `GET /documents/{doc_id}/audit`

**200** `{"events": [...]}`: the document's events in `seq` order. **404** if
there is no such document.

## `GET /audit`

**200** `{"events": [...]}`: all events in `seq` order, filtered by any of
these optional query parameters (all given filters must match):

| parameter | matches |
|---|---|
| `actor` | events whose `actor` is exactly this string |
| `action` | events with this action; must be one of the five actions above, otherwise **422** |
| `since` | events with `ts >= since` (unix seconds, a number; otherwise **422**) |

## Durability

The trail is stored under `storage_dir`. A new `create_app(...)` over the same
`storage_dir` returns every earlier event unchanged, and the events it appends
have larger `seq` values than all earlier ones.

Write tests for the trail, including a restart.

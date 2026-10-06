# Part 1: Confidence routing and a review queue (about 20 minutes)

Today every model answer is trusted. Operations wants a human to check the
documents the model is unsure about. After classification, each document is
either **auto-accepted** or put in a **review queue**, and reviewers resolve
the queue through the API.

Read `app/` first. Keep the
`create_app(storage_dir, llm, clock, auto_accept_threshold=0.8, consistency_samples=1)`
signature; in this part `consistency_samples` is always 1.

## Statuses

| status | meaning |
|---|---|
| `ingested` | uploaded, not classified yet (every accepted document starts here) |
| `auto_accepted` | the model was confident enough; final |
| `needs_review` | waiting in the review queue |
| `reviewed` | a reviewer chose the final label; final |

## Routing

When `POST /batches/{batch_id}/classify` classifies a document:

* the classification succeeded and `confidence >= auto_accept_threshold`
  → `auto_accepted`, `final_label` = the model's label;
* the classification succeeded and `confidence < auto_accept_threshold`
  → `needs_review` with `review_reason: "low_confidence"`;
* the classification failed (see the README) → `needs_review` with
  `review_reason: "classification_failed"`.

Calling `classify` again on a batch whose documents were already routed is
covered in Part 3; you may leave it as it is for now (the tests for this part
classify each batch once).

## The document object

Every endpoint that returns documents (`GET /batches/{batch_id}`, the classify
response, and the new endpoints below) returns the existing shape plus:

```json
{"...": "...", "classification": {"label": "id_document", "confidence": 0.66, "...": "..."},
 "status": "needs_review", "final_label": null, "review_reason": "low_confidence", "reviewed_by": null}
```

| field | `ingested` | `auto_accepted` | `needs_review` | `reviewed` |
|---|---|---|---|---|
| `final_label` | `null` | the model's label | `null` | the reviewer's label |
| `review_reason` | `null` | `null` | `low_confidence` / `classification_failed` | unchanged from `needs_review` |
| `reviewed_by` | `null` | `null` | `null` | the reviewer |

`classification` stays what the model said, even after a reviewer overrides it.

## `GET /documents/{doc_id}`

**200** with the document, **404** if there is no such document.

## `GET /review-queue`

**200** `{"items": [ ...documents... ]}`: every document currently in
`needs_review`, oldest first: ordered by the clock time at which it entered
`needs_review`, and for equal times in upload order (earlier batch first, then
row order). Documents leave the queue when they are reviewed.

## `POST /documents/{doc_id}/review`

JSON body `{"reviewer": "<string>", "label": "<label>"}`. Unknown keys are ignored.

* `reviewer` must be a string that is not empty after stripping surrounding
  whitespace; it is stored stripped.
* `label` must be exactly one of `contract`, `invoice`, `id_document`,
  `support_letter`, `other` (case-sensitive). It may agree with the model's
  label or override it.

| situation | status |
|---|---|
| `reviewer` or `label` missing or invalid | 422 (the document is unchanged) |
| unknown document | 404 |
| the document is not in `needs_review` (`ingested`, `auto_accepted`, already `reviewed`) | 409 |

On success the document becomes `reviewed` with `final_label` = `label` and
`reviewed_by` = the reviewer, and the response is **200** with the document.

404 and 409 bodies use FastAPI's `{"detail": "..."}` with a message that says
what is wrong (for example `"document DOC-1001 is auto_accepted, not needs_review"`).

## Constraints

* Everything is stored in SQLite under `storage_dir`: a new `create_app(...)`
  over the same `storage_dir` sees the same statuses and the same queue.
* `auto_accept_threshold` is a number between 0 and 1 (the tests use 0, 0.5,
  0.8, 0.96 and 1).
* Write tests for your work.

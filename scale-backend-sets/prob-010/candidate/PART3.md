# Part 3: Hardening for the review team (about 20 minutes)

The review UI is going live for a team of 30 reviewers who all work the same
queue, and last week an operator re-ran `classify` on a batch after a provider
outage and wiped out a day of human reviews. Everything from Parts 1 and 2
still holds unless this page changes it.

## 1. Versions and compare-and-set reviews

Every document gets an integer `version`: `1` when it is ingested, and `+1` on
every status change (so a reviewed document is at version 3). It is part of
the document object everywhere.

`POST /documents/{doc_id}/review` accepts an optional `"expected_version": <int>`.
If it is given and differs from the document's current version, respond
**409** and change nothing (no event). Without it, the Part 1 rules apply.

## 2. Concurrent reviews

Several reviewers may submit a review for the same document at the same
moment. Exactly one of them succeeds (**200**); every other one gets **409**.
The document's `final_label` and `reviewed_by` are the winner's, and its trail
has exactly one `reviewed` event, by the winner. No request may fail with a 500
(for example `database is locked`). The tests fire 8 threads at once.

## 3. Idempotent re-classification

`POST /batches/{batch_id}/classify` only calls the model for documents in
`ingested`. Documents in any other status are left untouched: no model call,
no audit event, no change to their classification, status or version. This
also holds for documents whose classification failed: they stay in the
review queue for a human.

The response still lists every document of the batch; `classified` and
`failed` count only the documents classified by this call (so a re-run
returns `0` and `0`).

Two `classify` calls on the same batch at the same time must not record a
document twice: every document ends with exactly one `classified` event and
one routing event, at version 2. (Calling the model twice for a document in
that race is acceptable; recording it twice is not.)

## 4. Self-consistency sampling

The same document sometimes gets different labels on different calls. With
`create_app(..., consistency_samples=2)`, classify each document **twice**, one
sample after the other, each sample a complete classification with its own
budget of up to 3 attempts, exactly as today:

* If the first sample fails, the classification fails with that error; the
  second sample is not attempted.
* If the second sample fails, the classification fails (`label` and
  `confidence` are `null`).
* `attempts` is the total number of model calls for the document across both samples.
* Otherwise the classification's `label` is the first sample's label and its
  `confidence` is the **lower** of the two confidences.
* If the two labels differ, the document goes to `needs_review` with
  `review_reason: "disagreement"`, whatever the confidence. If they agree, it is
  routed by the threshold as before.

With `consistency_samples=1` (the default) nothing changes. Any other value
than 1 or 2 makes `create_app` raise `ValueError`.

## 5. Discussion (no code required)

Be ready to talk about:

* the review queue at 100x volume: prioritising (age, SLA, document type,
  customer tier), assigning work to reviewers without two people opening the
  same document, and what happens when the queue grows faster than reviewers
  can drain it;
* choosing `auto_accept_threshold` from data: how you would use the reviewed
  documents to calibrate it, and per-label thresholds;
* making the audit log tamper-evident, and how long to keep it.

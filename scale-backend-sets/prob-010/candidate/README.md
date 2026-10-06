# Document intake service

Customers send us documents (contracts, invoices, ID scans, support letters)
in bulk. This service is already in production: it accepts a batch file,
validates and stores every document in SQLite, and classifies each document
with an LLM. Operations now wants humans in the loop for the documents the
model is unsure about, and compliance wants a full audit trail. You will extend
the service in three parts. Your interviewer gives you `PART1.md` first; the
next part comes when you finish.

**Read the existing code before you change it.** It is small (about 350 lines).

## Layout

```
app/main.py            create_app(): routes (start here)
app/db.py              DocumentStore: SQLite schema and queries (storage_dir/intake.db)
app/ingest.py          JSONL / CSV parsing and per-row validation
app/classifier.py      prompt, output parsing, retry loop -> Classification
mock_services/llm.py   make_llm(): the in-process mock LLM, its labels and keyword map
mock_services/clock.py RealClock / FakeClock (tests control time with FakeClock)
data/                  sample batches, including rows the API must reject
tests/                 tests for the existing endpoints; add yours here
```

## Setup

Python 3.10+ with `fastapi uvicorn httpx pydantic pytest python-multipart`.

```
python -m pytest                                         # run tests
uvicorn --factory app.main:create_app --port 8000        # data goes to ./storage/intake.db
curl -s -F file=@data/documents.jsonl localhost:8000/batches
curl -s -X POST localhost:8000/batches/<batch_id>/classify
```

## The API today

| endpoint | behaviour |
|---|---|
| `POST /batches` | Multipart upload, field `file`, a `.jsonl` or `.csv` file (case-insensitive) of documents `{doc_id, title, text}`. Each row is validated on its own (see `app/ingest.py`); `doc_id` must be unique across **all** batches. **201** `{"batch_id", "filename", "total_rows", "accepted": [doc ids in file order], "errors": [{"row", "error"}]}`. **415** for another extension, **400** for an empty / non-UTF-8 file or a CSV header without `doc_id,title,text`. |
| `GET /batches/{batch_id}` | **200** `{"batch_id", "filename", "total_rows", "errors", "created_at", "documents": [...]}` (documents in upload order), **404** if unknown. |
| `POST /batches/{batch_id}/classify` | Classifies every document of the batch with the model (again, if it was classified before) and stores the latest result. **200** `{"batch_id", "classified", "failed", "documents": [...]}`. A document whose classification failed is counted in `failed`, not an HTTP error. **404** if unknown. |
| `GET /health` | `{"status": "ok", "time": <clock time>}` |

A document looks like:

```json
{"doc_id": "DOC-1001", "batch_id": "3f2a...", "title": "msa_acme.pdf",
 "text": "Master services agreement ...", "created_at": 1700000000.0,
 "classification": {"label": "contract", "confidence": 0.83, "attempts": 1, "error": null,
                    "classified_at": 1700000000.0}}
```

`classification` is `null` until the document is classified. When the
classification failed (3 bad attempts, or a non-retryable model error),
`label` and `confidence` are `null` and `error` says why.

Labels: `contract`, `invoice`, `id_document`, `support_letter`, `other`.

## Rules

Open book: docs, search engines and Stack Overflow are fine; AI assistants are not.
Talk through your decisions. Tests are part of the deliverable.

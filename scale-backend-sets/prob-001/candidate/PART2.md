# Part 2: LLM classification (about 20 minutes)

Classify each valid ticket of an upload with the LLM and persist the results.

## The model

Use the client passed to `create_app` as `llm` (by default
`mock_services.llm.make_llm()`):

```python
resp = llm.complete(prompt, timeout=10)   # resp.text is the model's answer
```

* Put the ticket's `subject` and `body` inside `<item>...</item>` in the
  prompt. The model ignores everything outside the tags.
* Allowed labels: `billing`, `bug`, `account_access`, `feature_request`, `other`.
* The model is asked for `{"label": "<label>", "confidence": <0..1>}`, but its
  output is not always usable. Errors are subclasses of
  `shared.mock_llm.LLMError`; `err.retryable` tells you whether retrying can help.

## Valid output

After stripping surrounding whitespace and an optional markdown code fence
(```` ``` ```` or ```` ```json ````), the text must be a JSON object where:

* `label` is a string that, after trimming whitespace and lowercasing, is one
  of the allowed labels. Store the normalized form.
* `confidence` is a number (not a boolean) between 0 and 1 inclusive.

Anything else is an invalid output.

## Retries

Each ticket gets **at most 3 LLM calls** (attempts). Retry when the call raises
a retryable `LLMError` or returns invalid output. A non-retryable `LLMError`
fails the ticket immediately. Every call must pass `timeout=10`.

## `POST /uploads/{upload_id}/classify`

Classifies every valid ticket of the upload and returns **200**:

```json
{
  "upload_id": "...",
  "classified": 8,
  "failed": 1,
  "results": [
    {"ticket_id": "T-1001", "status": "classified", "label": "billing",
     "confidence": 0.93, "attempts": 1, "error": null},
    {"ticket_id": "T-1002", "status": "failed", "label": null,
     "confidence": null, "attempts": 3, "error": "<why the last attempt failed>"}
  ]
}
```

* `results` has one entry per valid ticket, in upload order.
* `attempts` is the number of LLM calls made for that ticket.
* A failed ticket does not fail the request: it is reported with
  `status: "failed"` and a non-empty `error`.
* **404** if the upload does not exist.

Persist the response object to `<storage_dir>/classifications/<upload_id>.json`.

## `GET /uploads/{upload_id}/classifications`

**200** with the persisted object; **404** if the upload does not exist or has
not been classified yet.

Write tests that cover the failure modes, using `make_llm(LLMConfig(...))` to
inject them (see `shared/README.md`: `prompt_faults`, `fault_script`,
`fenced_rate`, ...).

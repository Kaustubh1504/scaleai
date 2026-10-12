# 06. Fix the broken API script

A teammate wrote a small ops script against the **Workforce API**: list
annotators, then hand out labeling tasks to the active ones round-robin. It
"worked on their machine" and now fails on every run. They're out today and
the tasks need assigning. Your file is **their script**, not stubs.

## The API

* Every request needs `Authorization: Bearer <token>`.
* `GET /v1/annotators?page=<n>&per_page=<1..100>&status=<active|onboarding|suspended>`
  (all optional) returns
  `{"data": [...], "page", "per_page", "total", "total_pages"}`, ordered by id.
* `POST /v1/tasks/{task_id}/assignments` with a **JSON** body
  `{"annotator_id": "ann_001"}` returns **201**
  `{"id": "asg_0001", "task_id": "task_001", "annotator_id": "ann_001", "status": "assigned"}`.
* Errors come back as `{"error": "<code>", "message": "<what went wrong>"}`
  and sometimes extra fields or headers. **Read them.**

## Setup

```python
from problem_api import make_api, TOKEN
client = make_api().client()   # make_api(n_annotators=23, n_tasks=8); TOKEN is a valid token
```

Your file already contains the teammate's script. Its
`if __name__ == "__main__":` block is what the Run button executes: it runs
the script the way the teammate did, so you see the failure.

## Your task

The script has **three bugs**. Find and fix them so that these work as their
docstrings say:

* `list_annotators(client: httpx.Client, token: str, status: str | None = None, page_size: int = 25) -> list[dict]`
* `assign_task(client: httpx.Client, token: str, task_id: str, annotator_id: str) -> dict`
* `assign_round_robin(client: httpx.Client, token: str, task_ids: list[str]) -> list[dict]`
  (`ValueError` if nobody is active)

Rules:

* Don't change any function signature or what a function returns.
* Keep `resp.raise_for_status()` as the error handling: non-2xx should still
  raise `httpx.HTTPStatusError`.
* Fix the bugs; don't rewrite the script. A good fix is a few changed lines.

## Example

```python
list_annotators(client, TOKEN, page_size=10)   # 23 annotators, 3 requests
assign_round_robin(client, TOKEN, ["task_001", "task_002"])
# [{"id": "asg_0001", "task_id": "task_001", "annotator_id": "ann_001", ...}, {"id": "asg_0002", ..., "annotator_id": "ann_002", ...}]
```

## Constraints

* Debug from what the API tells you: status, headers, body, the URL you sent.
  Don't read `problem_api.py`.
* Note each bug and why it broke things: in the interview you'd explain them out loud.

<details><summary>Hint 1</summary>

`raise_for_status()` tells you the status and URL but not the body. Before
it, temporarily print what was actually sent (`resp.request.url`, its
headers and `content`) and what came back (`resp.status_code`,
`resp.headers`, `resp.text`).
</details>

<details><summary>Hint 2</summary>

Fix one error at a time and rerun: a 401 hides whatever is wrong behind it.
Expect to see a 401, then a 400, then a 415. Look at the `WWW-Authenticate`
header and any `allowed` field in the error body.
</details>

## Follow-up (talk it through)

* What would have caught each of these bugs before they shipped?
* Why does the server reject an unknown query parameter instead of ignoring
  it? What does silently ignoring it cost?
* `data=` vs `json=` vs `content=` in httpx: when would you use each?

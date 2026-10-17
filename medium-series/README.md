# Copy-paste backend snippets

`snippets.md`: standalone functions. Each `# snippet:` block has its own imports and config and never calls another snippet; paste one and go.

`tests/test_snippets.py` runs every block alone in a fresh namespace and then tests it: `python3 -m pytest tests -q`

## Posting to Medium
- Medium doesn't render pasted Markdown. Open `snippets.md` in VS Code's preview (Cmd+Shift+V), copy the rendered view, and paste it into Medium.
- For long blocks, put each snippet in its own GitHub Gist and paste the gist URL on its own line; Medium embeds it with syntax highlighting.

## Articles (`articles/`)
Step-by-step tutorials. The final code blocks are copied exactly from `snippets.md`, so they're the tested versions.
1. `01-reliable-llm-call.md`: ask_llm + fake_http
2. `02-flaky-apis.md`: request_with_retries, fetch_all_pages, bounded_map, bounded_gather
3. `03-webhooks.md`: send_webhook, verify_signature, insert_once
4. `04-csv-endpoint.md`: fastapi_endpoint, safe_path, read_csv, rows_by_id, atomic_write_json, json_cache
5. `05-fastapi-blocks.md`: add_request_id, add_rate_limit, background_jobs, update_if_version
6. `06-logic-patterns.md`: grouping/dedupe, join/diff, consensus, time/money, chunks/bfs, schedule
7. `07-messy-data.md`: messy_json, redact_pii
8. `08-state-and-leases.md`: state_machine, leases
9. `09-api-clients.md`: token_provider, client_rate_limiter, ttl_cache
10. `10-sync-and-big-files.md`: incremental_sync, jsonl
11. `11-queues-and-budgets.md`: priority_queue, retry_pool, token_budget
12. `12-reports-and-apis.md`: rank, paginate, audit_and_metrics, read_upload, iou
13. `13-batching-llm-calls.md`: ask_llm_batch
14. `14-idempotent-intake.md`: fake_clock, idempotency_keys, token_bucket, sqlite_store
15. `15-scheduled-retries-and-crawls.md`: retry_schedule, get_json_with_retries, async_retries
16. `16-routing-and-reports.md`: worker_routing, stats_helpers

Rebuild the Medium pages after editing an article: `python3 build_html.py` (needs `pip install markdown`).

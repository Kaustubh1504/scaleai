# set-021 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does replay() do for each request row?

For `publish` it bumps the backend version for the model and calls `cache.drop_model`. For `fetch` it builds a key with `make_key`, calls `cache.get(key, req.ts)`, and records a hit if an entry comes back. Otherwise it calls the backend, stores a new CacheEntry with `expires_at = ts + ttl`, and records a miss. Per-model counts live in ModelStats.

### 2. Where does the TTL for a model come from?

`load_config` reads `default_ttl_seconds` and the `ttl_seconds` map, lower-casing and trimming model names and converting values with int(). `replay` uses `ttls.get(model, default_ttl)`, so ner-v3 (no override) gets 300 seconds.

### 3. When is purge_expired called?

Only once, in `build_report`, at the ts of the last log row, before the snapshot is built. Lookups during the replay never call it.

### 4. What does a CacheEntry hold?

task_id, model, locale, value, stored_at and expires_at. The snapshot is built from these entry fields, not from the cache keys.

### 5. How is a blank locale handled?

`norm_locale` returns the trimmed lower-cased value or `en-us` if that is empty. `load_requests` only applies it to `fetch` rows; publish rows get an empty locale.

### 6. How does report_json differ from build_report?

It calls build_report and passes the result to json.dumps with indent=2, sort_keys=True and default=str.

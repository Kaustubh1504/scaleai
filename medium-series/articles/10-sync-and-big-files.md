# Incremental Sync and Huge Files in Python, Step by Step

### Keep a local copy of an API in sync, and process files too big for memory

Two jobs come up in almost every data backend:

- **Mirror an upstream API** without downloading everything every time, and without losing deletes.
- **Process files bigger than RAM**, and resume after a crash without duplicating output.

We'll build two standalone snippets: `sync()` with `apply_changes()`, and the JSONL helpers `iter_jsonl()`, `append_jsonl()` and `count_complete_lines()`.

**What you need:** Python 3.9+. Standard library only.

---

## Part 1: Incremental sync

### Step 1: Why a full re-download doesn't scale

Fetching all 2 million records every five minutes is slow, expensive, and hard on the upstream. Most APIs let you ask for changes only: `GET /records?updated_since=...`.

### Step 2: Keep a watermark

The **watermark** is the highest `updated_at` value you've fully processed. Next run, ask for everything changed since then. Save it alongside your data.

### Step 3: Ask for `>=`, not `>`

If two records share the same timestamp and your previous run stopped between them, `updated_since > watermark` skips the second one forever. Ask for **at or after** the watermark, and make replays harmless (next step).

### Step 4: Make applying a change idempotent

When a record arrives, compare versions:

- **Newer than what you have:** store it.
- **Same or older:** skip it. It's a replay, or it arrived out of order.

Now re-running a sync, or overlapping two pages, can never corrupt your data.

### Step 5: Keep deletes as tombstones

If the upstream marks a deletion with `"deleted": true` and you simply drop the row, an *older* update replayed later brings it back. Keep the deletion record as a **tombstone** (it has the newest version, so older updates are skipped), and filter tombstones out when reading.

### Step 6: Move the watermark only after the data is safe

Move the watermark forward **after** every page has been applied. If you crash halfway, the next run starts from the old watermark and replays pages, which Step 4 makes harmless. If you saved the watermark first and then crashed, those records would be lost for good.

### The complete snippet

```python
def apply_changes(store: dict, records, key: str = "id", version: str = "updated_at") -> dict:
    """Upsert into store {id: record}: newer version wins, older or equal replays are skipped.
    Deletes arrive as records with "deleted": true and are kept as tombstones (so an old update
    can't resurrect them). Live rows: [r for r in store.values() if not r.get("deleted")]."""
    counts = {"upserted": 0, "deleted": 0, "skipped": 0, "max_version": None}
    for rec in records:
        k, v = rec[key], rec[version]
        if counts["max_version"] is None or v > counts["max_version"]:
            counts["max_version"] = v
        current = store.get(k)
        if current is not None and current[version] >= v:
            counts["skipped"] += 1
            continue
        store[k] = rec
        counts["deleted" if rec.get("deleted") else "upserted"] += 1
    return counts


def sync(fetch_page, store: dict, state: dict, key: str = "id", version: str = "updated_at") -> dict:
    """fetch_page(since, cursor) -> (records, next_cursor), records changed at/after `since`.
    Applies every page, then advances state["watermark"]. Re-running after a crash is safe:
    replays are skipped. Persist store + state (atomically) after it returns."""
    since, cursor = state.get("watermark"), None
    totals = {"upserted": 0, "deleted": 0, "skipped": 0}
    high = since
    while True:
        records, cursor = fetch_page(since, cursor)
        c = apply_changes(store, records, key, version)
        for k in totals:
            totals[k] += c[k]
        if c["max_version"] is not None and (high is None or c["max_version"] > high):
            high = c["max_version"]
        if not cursor:
            break
    state["watermark"] = high
    return totals
```

### Step 7: Run it and persist the result

```python
store = load_cache("output/store.json")         # json_cache snippet from part 4
state = load_cache("output/state.json")

def fetch_page(since, cursor):
    params = {"updated_since": since} if since else {}
    if cursor:
        params["cursor"] = cursor
    body = request_with_retries("GET", f"{BASE}/records", params=params).json()
    return body["data"], body.get("next_cursor")

totals = sync(fetch_page, store, state)
save_cache("output/store.json", store)          # data first
save_cache("output/state.json", state)          # then the watermark
```

---

## Part 2: Files too big for memory

### Step 8: Use JSONL for big data

A single JSON array has to be parsed all at once. **JSON Lines**, one object per line, can be read one line at a time, appended to without rewriting the file, and survives a crash with at most one damaged line at the end.

### Step 9: Stream it in, and skip bad lines

Iterate over the open file instead of calling `read()`, so memory stays flat whether the file is 1 MB or 50 GB. Record bad lines (with their line numbers) instead of crashing on them.

### Step 10: Append safely

Open in append mode, write each record followed by `\n`, then `flush()` and `fsync()` so the data really reaches the disk before you count it as done.

### Step 11: Resume from where you stopped

After a crash, count the lines that end with a newline. A half-written last line doesn't count. That number tells you how many records were finished, so you continue from the next one.

### The complete snippet

```python
import json
import os


def iter_jsonl(path, errors=None):
    """Yield (line_no, obj) one line at a time (constant memory). Bad lines -> errors, skipped."""
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield n, json.loads(line)
            except ValueError:
                if errors is not None:
                    errors.append({"line": n, "error": "invalid_json"})


def append_jsonl(path, records) -> int:
    """Append records, one JSON object per line, and fsync. Returns how many were written."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
        f.flush()
        os.fsync(f.fileno())
    return n


def count_complete_lines(path) -> int:
    """Lines that end in a newline: where to resume after a crash (a torn last line doesn't count)."""
    if not os.path.exists(path):
        return 0
    with open(path, "rb") as f:
        return sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b""))
```

### Step 12: A resumable export

```python
done = count_complete_lines("output/export.jsonl")
batch = []
for n, record in iter_jsonl("data/huge_input.jsonl", errors):
    if n <= done:
        continue                               # finished before the crash
    batch.append(transform(record))
    if len(batch) == 500:
        append_jsonl("output/export.jsonl", batch)
        batch = []
append_jsonl("output/export.jsonl", batch)
```

This uses line numbers as the resume key and assumes no blank lines in the input. For an input with blank or invalid lines, save the last processed `n` in a small checkpoint file instead.

---

## Testing

```python
def test_sync_handles_deletes_and_replays():
    pages = {(None, None): ([{"id": "a", "updated_at": 1}, {"id": "b", "updated_at": 2}], "p2"),
             (None, "p2"): ([{"id": "a", "updated_at": 3, "deleted": True}], None)}
    store, state = {}, {}
    sync(lambda since, cur: pages[(since, cur)], store, state)
    assert state["watermark"] == 3
    assert [r["id"] for r in store.values() if not r.get("deleted")] == ["b"]
    assert apply_changes(store, [{"id": "a", "updated_at": 1}])["skipped"] == 1   # no resurrection


def test_torn_last_line(tmp_path):
    p = tmp_path / "x.jsonl"
    append_jsonl(p, [{"a": 1}, {"a": 2}])
    with open(p, "a") as f:
        f.write('{"torn"')                     # simulated crash mid-write
    assert count_complete_lines(p) == 2
```

---

## Recap

1. **Sync from a watermark,** asking for changes *at or after* it.
2. **Apply changes idempotently:** newer versions win, replays are skipped.
3. **Keep deletes as tombstones** so old updates can't bring rows back.
4. **Advance the watermark only after the data is saved.**
5. For huge data, **stream JSONL**: read line by line, append with `fsync`, and resume by counting complete lines.

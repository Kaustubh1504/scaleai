# Backend Building Blocks in Python, Step by Step: Rankings, Pagination, Audit Logs, Uploads, and IoU

### Five small snippets that come up in almost every reporting or data-quality service

This last tutorial collects five smaller patterns. Each is short, and each has a classic bug that's easy to ship:

1. **Ranking with ties:** is it 1, 2, 2, 3 or 1, 2, 2, 4?
2. **Paginating your own API:** why offset pagination skips rows.
3. **Audit logs and metrics:** an answer to "what happened, and how slow was it?"
4. **File uploads:** size, type and encoding checks *before* parsing.
5. **IoU for bounding boxes:** for when you need to score annotation quality.

**What you need:** Python 3.9+, `pip install fastapi python-multipart` for the upload section.

---

## 1. Ranking with ties

### Step 1: Sorting isn't ranking

`enumerate(sorted(...), 1)` gives two players with the same score different ranks. Tied scores should share a rank.

### Step 2: Choose a tie style

- **Competition ranking (1, 2, 2, 4):** sports and most leaderboards. After a tie, the next rank skips ahead.
- **Dense ranking (1, 2, 2, 3):** no gaps.

### Step 3: Make the order inside a tie deterministic

Tied players still need a stable order in the output (by name or ID), or your API returns them in a different order on each request.

```python
def rank(items, score, tiebreak=None, method: str = "competition", descending: bool = True) -> list:
    """[(rank, item)]. Ties share a rank. competition: 1, 2, 2, 4   dense: 1, 2, 2, 3.
    `tiebreak(item)` orders tied items (e.g. by name) so the output is deterministic."""
    def sort_key(it):
        s = score(it)
        return (-s if descending else s, tiebreak(it) if tiebreak else 0)

    out, prev, current = [], object(), 0
    for i, it in enumerate(sorted(items, key=sort_key), 1):
        s = score(it)
        if s != prev:
            current = i if method == "competition" else current + 1
            prev = s
        out.append((current, it))
    return out
```

```python
for r, row in rank(annotators, score=lambda a: a["accuracy"], tiebreak=lambda a: a["id"]):
    print(r, row["id"], row["accuracy"])
```

---

## 2. Paginating your own endpoint

### Step 4: Why `?page=2` breaks

Offset pagination (`items[20:40]`) shifts when rows are inserted. If a new row lands on page 1 while a client is reading, the last item of page 1 moves to page 2 and is shown twice, or a deleted row makes another one disappear.

### Step 5: Keyset pagination

Sort by a unique key, and return the items **after the last key the client saw**. New rows can't shift a page the client hasn't asked for yet.

### Step 6: Make the cursor opaque

Encode the last key as base64 JSON. Clients pass it back without depending on its format, so you can change it later. A cursor that won't decode means a **400**.

### Step 7: Clamp the limit

Never let `?limit=1000000` through. Clamp it to a maximum.

```python
import base64
import json


def encode_cursor(value) -> str:
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode()


def decode_cursor(cursor: str):
    """ValueError on garbage (map to 400)."""
    try:
        value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except Exception:
        raise ValueError("invalid cursor") from None
    return tuple(value) if isinstance(value, list) else value


def paginate(items, limit: int = 20, cursor=None, key=lambda it: it["id"], max_limit: int = 100) -> dict:
    """Sort by key, return up to `limit` items after the cursor + next_cursor (None on the last page).
    Keyset, not offset: rows added between requests don't shift pages. Filter items before calling."""
    limit = max(1, min(int(limit), max_limit))
    ordered = sorted(items, key=key)
    if cursor:
        after = decode_cursor(cursor)
        ordered = [it for it in ordered if key(it) > after]
    page = ordered[:limit]
    next_cursor = encode_cursor(key(page[-1])) if len(ordered) > limit else None
    return {"data": page, "next_cursor": next_cursor}
```

```python
@app.get("/tasks")
def list_tasks(status: str = None, limit: int = Query(20, ge=1, le=100), cursor: str = None):
    rows = [t for t in TASKS if status is None or t["status"] == status]     # filter first
    try:
        return paginate(rows, limit, cursor, key=lambda t: (-t["created_ts"], t["id"]))  # newest first
    except ValueError:
        raise HTTPException(400, "invalid cursor")
```

Including the ID in the key makes it unique even when two rows share a timestamp.

---

## 3. Audit logs and metrics

### Step 8: Use an append-only audit log

For anything a person might question later (payouts, status changes, deletions), append one JSON line per event, with a UTC timestamp. Never rewrite these lines. A lock keeps lines written by different threads from interleaving.

### Step 9: Use counters and timings for metrics

Count events (`llm.calls`, `cache.hits`) and time operations with a context manager. Report percentiles (p50, p95) rather than averages, because averages hide the slow tail that users actually notice.

```python
import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

_audit_lock = threading.Lock()


def audit_log(path, event: str, **fields) -> None:
    """Append one JSON line: {"ts", "event", ...fields}. Append-only; never rewrite history."""
    line = json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields},
                      ensure_ascii=False, default=str)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with _audit_lock, open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def new_metrics() -> dict:
    return {"counts": {}, "timings": {}, "lock": threading.Lock()}


def inc(metrics: dict, name: str, n: int = 1) -> None:
    with metrics["lock"]:
        metrics["counts"][name] = metrics["counts"].get(name, 0) + n


@contextmanager
def timed(metrics: dict, name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - start) * 1000
        with metrics["lock"]:
            metrics["timings"].setdefault(name, []).append(ms)


def snapshot(metrics: dict) -> dict:
    """{"counts": {...}, "timings": {name: {"count", "p50_ms", "p95_ms", "max_ms"}}}: serve at GET /metrics."""
    def pct(values, p):
        return round(values[min(len(values) - 1, int(round(p * (len(values) - 1))))], 2)

    with metrics["lock"]:
        timings = {k: sorted(v) for k, v in metrics["timings"].items()}
        counts = dict(metrics["counts"])
    return {"counts": counts,
            "timings": {k: {"count": len(v), "p50_ms": pct(v, 0.5), "p95_ms": pct(v, 0.95),
                            "max_ms": round(v[-1], 2)} for k, v in timings.items() if v}}
```

```python
metrics = new_metrics()

def classify(item):
    inc(metrics, "llm.calls")
    with timed(metrics, "llm.latency"):
        label = ask_llm(...)
    if label is None:
        inc(metrics, "llm.failures")
    audit_log("output/audit.jsonl", "classified", item_id=item["id"], label=label)
    return label

@app.get("/metrics")
def get_metrics():
    return snapshot(metrics)
```

Never log secrets or raw PII here. Run text through the `redact` snippet from part 7 first.

---

## 4. Validating file uploads

### Step 10: Check the cheap things first

Check the extension before reading anything (**415 Unsupported Media Type**).

### Step 11: Never read an unbounded upload

`await file.read()` loads the whole upload into memory. Read at most `max_bytes + 1`. If you got more than `max_bytes`, the file is too large (**413**), and you never held more than the limit in memory.

### Step 12: Decode and check it isn't empty

Decode with `utf-8-sig` (which strips Excel's BOM). Invalid bytes or a blank file mean **422**.

```python
from pathlib import Path

from fastapi import HTTPException, UploadFile


async def read_upload(file: UploadFile, max_bytes: int = 5_000_000, extensions=(".csv",)) -> str:
    """415 wrong extension, 413 too large, 422 empty or not UTF-8. Returns the decoded text (BOM stripped).
    Reads at most max_bytes + 1, so a huge upload is never fully loaded."""
    if not file.filename or Path(file.filename).suffix.lower() not in extensions:
        raise HTTPException(415, f"expected one of {', '.join(extensions)}")
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"file larger than {max_bytes} bytes")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "file is not valid UTF-8") from None
    if not text.strip():
        raise HTTPException(422, "file is empty")
    return text
```

```python
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    text = await read_upload(file, max_bytes=5_000_000)
    records = [[v.strip() for v in row] for row in csv.reader(io.StringIO(text, newline=""))]
    ...
```

---

## 5. IoU for bounding boxes

### Step 13: Intersection over union

To compare two boxes, divide the area where they overlap by the total area they cover together. 1.0 is a perfect match, 0.0 is no overlap. Clamp negative overlaps to zero, and guard against zero-area boxes to avoid dividing by zero.

### Step 14: Know your box format

APIs mix `(x1, y1, x2, y2)` corners with `(x, y, width, height)`. Convert to one format before comparing. This is the most common IoU bug.

### Step 15: Match boxes one-to-one

To score an annotator's boxes against gold boxes, pair them greedily, best IoU first, and use each box at most once. Pairs below the threshold (often 0.5) don't count. Then precision = matches / predictions, and recall = matches / gold boxes.

```python
def xywh_to_xyxy(box):
    x, y, w, h = box
    return (x, y, x + w, y + h)


def iou(a, b) -> float:
    """Boxes as (x1, y1, x2, y2). 0.0 when they don't overlap or have zero area."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def match_boxes(preds, golds, threshold: float = 0.5):
    """Greedy one-to-one matching, best IoU first. Returns (matches [(pred_i, gold_i, iou)],
    unmatched_pred_indexes, unmatched_gold_indexes). precision = matches/len(preds), recall = matches/len(golds)."""
    pairs = sorted(((iou(p, g), i, j) for i, p in enumerate(preds) for j, g in enumerate(golds)),
                   key=lambda t: (-t[0], t[1], t[2]))
    used_p, used_g, matches = set(), set(), []
    for score, i, j in pairs:
        if score < threshold:
            break
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j, round(score, 4)))
    return (matches, [i for i in range(len(preds)) if i not in used_p],
            [j for j in range(len(golds)) if j not in used_g])
```

```python
matches, extra, missed = match_boxes([xywh_to_xyxy(b) for b in annotator_boxes],
                                     [xywh_to_xyxy(b) for b in gold_boxes], threshold=0.5)
precision = len(matches) / len(annotator_boxes) if annotator_boxes else 1.0
recall = len(matches) / len(gold_boxes) if gold_boxes else 1.0
```

---

## Testing

```python
def test_rank_ties():
    rows = [{"n": "b", "s": 9}, {"n": "a", "s": 9}, {"n": "c", "s": 7}]
    assert [r for r, _ in rank(rows, lambda r: r["s"], tiebreak=lambda r: r["n"])] == [1, 1, 3]


def test_pages_dont_shift():
    items = [{"id": i} for i in range(5)]
    p1 = paginate(items, limit=2)
    p2 = paginate(items + [{"id": -1}], limit=2, cursor=p1["next_cursor"])   # row added meanwhile
    assert [i["id"] for i in p2["data"]] == [2, 3]


def test_iou():
    assert iou((0, 0, 2, 2), (1, 1, 3, 3)) == pytest.approx(1 / 7)
    assert iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0
```

---

## Recap

1. **Rank** with shared ranks for ties, and a deterministic order within ties.
2. **Paginate** with a key cursor, not offsets. Make it opaque and clamp the limit.
3. Keep an **append-only audit log** and **percentile timings**.
4. **Check uploads** in order: type (415), bounded read (413), decoding (422).
5. **IoU:** normalize the box format, guard against division by zero, and match one-to-one before computing precision and recall.

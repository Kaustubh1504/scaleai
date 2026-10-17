# Build a FastAPI Endpoint That Processes Untrusted CSV Files, Step by Step

### Safe paths, messy rows, per-row errors, atomic writes, and resumable runs

"Read a CSV and write JSON" sounds like a warm-up exercise, until real files arrive. One starts with an invisible byte-order mark. Another has a description that contains a comma, a quote and a line break. One is Latin-1. And someone sends `../../etc/passwd.csv` as the file path.

In this tutorial we'll build a `POST /convert` endpoint that joins a `tasks.csv` to a `users.csv` and writes JSON. Each step adds one standalone function you can reuse in any project.

**What you need:** Python 3.9+, `pip install fastapi uvicorn httpx`.

**The request:**

```json
{"tasks_path": "data/tasks.csv", "users_path": "data/users.csv", "output_path": "output/tasks.json"}
```

**The response:** how many rows were written, plus a list of per-row errors.

---

## Step 1: Sketch the endpoint and its status codes

Before writing any logic, decide which failure gets which status code, and in what order you check them:

- **503:** the server is missing config (an API key, for example)
- **400:** a bad path
- **404:** an input file doesn't exist
- **422:** a file is unreadable, or the request body is invalid
- **200:** success, even if some *rows* had problems

Here's a skeleton that encodes that order:

```python
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Req(BaseModel):
    input_path: str
    output_path: str


@app.post("/process")
def process(req: Req):                        # def, not async: blocking work runs in a thread pool
    # 1. config (503) -> 2. paths (400) -> 3. files exist (404) -> 4. parse (422) -> 5. work -> 6. write
    missing = [n for n in ("OPENAI_API_KEY",) if not os.environ.get(n)]
    if missing:
        raise HTTPException(503, f"missing config: {', '.join(missing)}")
    errors: list[dict] = []
    results: list[dict] = []
    # ... paste safe_path / read_csv / rows_by_id / ask_llm / atomic_write_json here ...
    return {"rows_written": len(results), "errors": errors}
```

Use a plain `def`, not `async def`. File reading is blocking, and FastAPI runs `def` endpoints in a thread pool for you. Pydantic already turns a malformed request body into a 422.

---

## Step 2: Never trust a path

### The wrong way

```python
if raw.startswith("data/"):   # "data/../secrets.csv" passes!
```

Checking the string misses `..` segments and symlinks.

### The right way: resolve first, then check

`Path.resolve()` collapses `..` and follows symlinks. Only *then* do you check that the result is still inside the allowed folder:

```python
from pathlib import Path

from fastapi import HTTPException


def safe_path(raw: str, root: str, ext: str) -> Path:
    """400 if absolute, wrong extension, or (after resolving .. and symlinks) outside root."""
    p = Path(raw)
    if not raw or p.is_absolute() or p.suffix != ext:
        raise HTTPException(400, f"bad path: {raw}")
    resolved = p.resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise HTTPException(400, f"bad path: {raw}")
    return resolved
```

**Validate every path before reading anything.** If the output path is bad, you shouldn't have spent time parsing the inputs first.

---

## Step 3: Read the CSV properly

We'll build this up from the naive version.

**Naive:** `line.split(",")` breaks on `"Smith, John"`. Use the `csv` module, which handles quoted commas, `""` escaped quotes, and fields that span several lines.

**BOM:** Excel often saves UTF-8 with an invisible byte-order mark at the start. Then your first header is `"﻿task_id"`, and every lookup by `task_id` fails. Decoding with `utf-8-sig` strips it.

**Encoding:** decode the bytes yourself, so a Latin-1 file becomes a clean 422 instead of a crash halfway through parsing.

**Whitespace and blank lines:** strip every value, and drop rows where every field is empty.

**Row numbers:** count *parsed records*, not file lines. A quoted field that spans two lines is still one record, and your error messages must point at the right row.

**Headers:** check only the *required* columns. Extra columns pass through untouched.

Put together:

```python
import csv
import io
from pathlib import Path

from fastapi import HTTPException


def read_csv(path: Path, required: list[str]) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """(header, [(row_no, values)]); row_no counts records from 1, header excluded.
    404 missing file, 422 not UTF-8 / empty / missing required header."""
    if not path.is_file():
        raise HTTPException(404, f"{path.name} not found")
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, f"{path.name} is not valid UTF-8") from None
    records = [[v.strip() for v in row] for row in csv.reader(io.StringIO(text, newline=""))]
    records = [r for r in records if any(r)]
    if not records:
        raise HTTPException(422, f"{path.name} is empty")
    header = records[0]
    missing = [c for c in required if c not in header]
    if missing:
        raise HTTPException(422, f"{path.name} missing columns: {', '.join(missing)}")
    return header, list(enumerate(records[1:], 1))
```

---

## Step 4: Validate rows, and keep going when one is bad

One bad row must never fail the whole request. Instead, skip it (or keep it with a null) and record an error the caller can act on.

Almost every CSV has an ID column, and the same three checks apply to it every time:

```python
def rows_by_id(header: list[str], rows, id_col: str, file: str, errors: list) -> list[tuple[int, dict]]:
    """Skips malformed rows, empty ids and repeat ids (first wins); skipped rows aren't "seen".
    Appends {"file", "row", "id", "error"} with malformed_row / missing_<id_col> / duplicate_<id_col>."""
    kept, seen = [], set()
    for n, values in rows:
        if len(values) != len(header):
            errors.append({"file": file, "row": n, "id": None, "error": "malformed_row"})
            continue
        row = dict(zip(header, values))
        rid = row[id_col]
        if not rid:
            errors.append({"file": file, "row": n, "id": None, "error": f"missing_{id_col}"})
            continue
        if rid in seen:
            errors.append({"file": file, "row": n, "id": rid, "error": f"duplicate_{id_col}"})
            continue
        seen.add(rid)
        kept.append((n, row))
    return kept
```

Note the line `seen.add(rid)`: it runs only when a row is *kept*. A malformed row with ID `A` shouldn't make the next valid `A` look like a duplicate.

Now add the rules specific to your data. For each rule, decide whether to **skip the row** or **keep it with a null**:

- A row with no ID can't be referenced, so skip it.
- A row with a bad priority is still a real task, so keep it with `priority: null` and report the error.

```python
errors = []
uh, ur = read_csv(users_path, ["user_id"])
users = {u["user_id"]: u for _, u in rows_by_id(uh, ur, "user_id", "users", errors)}

th, tr = read_csv(tasks_path, ["task_id", "title", "user_id", "priority"])
out = []
for n, task in rows_by_id(th, tr, "task_id", "tasks", errors):
    tid = task["task_id"]
    task["priority"] = int(task["priority"]) if task["priority"] in ("1", "2", "3") else None
    if task["priority"] is None:
        errors.append({"file": "tasks", "row": n, "id": tid, "error": "invalid_priority"})
    task["user"] = users.get(task["user_id"])
    if task["user"] is None:
        code = "missing_user_id" if not task["user_id"] else "unknown_user"
        errors.append({"file": "tasks", "row": n, "id": tid, "error": code})
    out.append(task)
```

Why `in ("1", "2", "3")` instead of `int(...)`? `int(" 2")` succeeds, but `int("2.0")` raises. An explicit allowlist can't surprise you.

---

## Step 5: Write the output atomically

If you write straight to `output/tasks.json` and the process crashes halfway through, a reader sees half a file. And if the request fails, the previous good output is already gone.

The fix: write to a temp file **in the same folder**, then `os.replace` it over the target. That rename is atomic, so readers see either the old file or the new one, never a mix.

```python
import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, data) -> None:
    """Readers see the old file or the new one, never half. No temp file left behind on failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)          # fail before touching disk
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

Three details:

- **Serialize before touching the disk.** A serialization error then leaves everything untouched.
- **`fsync` before the rename,** so a power cut can't leave you with a renamed but empty file.
- **Same folder, not `/tmp`.** `os.replace` is only atomic within a single filesystem.

---

## Step 6: Assemble the endpoint

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ConvertRequest(BaseModel):
    tasks_path: str
    users_path: str
    output_path: str


@app.post("/convert")
def convert(req: ConvertRequest):
    tasks_path = safe_path(req.tasks_path, "data", ".csv")          # all paths first
    users_path = safe_path(req.users_path, "data", ".csv")
    output_path = safe_path(req.output_path, "output", ".json")

    errors = []
    uh, ur = read_csv(users_path, ["user_id"])
    users = {u["user_id"]: u for _, u in rows_by_id(uh, ur, "user_id", "users", errors)}

    th, tr = read_csv(tasks_path, ["task_id", "title", "user_id", "priority"])
    out = []
    for n, task in rows_by_id(th, tr, "task_id", "tasks", errors):
        tid = task["task_id"]
        task["priority"] = int(task["priority"]) if task["priority"] in ("1", "2", "3") else None
        if task["priority"] is None:
            errors.append({"file": "tasks", "row": n, "id": tid, "error": "invalid_priority"})
        task["user"] = users.get(task["user_id"])
        if task["user"] is None:
            code = "missing_user_id" if not task["user_id"] else "unknown_user"
            errors.append({"file": "tasks", "row": n, "id": tid, "error": code})
        out.append(task)

    atomic_write_json(output_path, out)
    return {"rows_written": len(out), "errors": errors}
```

Run it with `uvicorn main:app --reload` from the folder that contains `data/` and `output/`.

---

## Step 7: Make re-runs free (checkpoint and resume)

Suppose each row also needs an expensive call, such as an LLM classification. After a crash at row 1,500 of 2,000, you don't want to pay for rows 1 to 1,499 again. And when only one row changes, only that row should be recomputed.

Cache each result under a hash of the inputs that affect it. Changed input means a new key, which means it gets recomputed:

```python
import hashlib
import json
import os
import tempfile
from pathlib import Path


def cache_key(*parts) -> str:
    """Stable key from the inputs that affect the result: changed input -> new key -> recompute."""
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_cache(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(path, cache: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

```python
cache = load_cache("output/.cache.json")

def classify_cached(task):
    k = cache_key(task["title"], task["description"])
    if k not in cache:
        result = ask_llm(...)               # from part 1 of this series
        if result is not None:              # don't cache failures: they retry next run
            cache[k] = result
    return cache.get(k)

categories = bounded_map(classify_cached, out, 5)
save_cache("output/.cache.json", cache)
```

---

## Step 8: Test the edge cases

```python
import pytest
from fastapi import HTTPException


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.mark.parametrize("raw", ["../x.csv", "/etc/x.csv", "data/../x.csv", "data/x.txt"])
def test_bad_paths(cwd, raw):
    with pytest.raises(HTTPException) as e:
        safe_path(raw, "data", ".csv")
    assert e.value.status_code == 400


def test_symlink_escape(cwd):
    (cwd / "secret.csv").write_text("x")
    (cwd / "data/link.csv").symlink_to(cwd / "secret.csv")
    with pytest.raises(HTTPException):
        safe_path("data/link.csv", "data", ".csv")


def test_messy_csv(cwd):
    p = cwd / "data/t.csv"
    p.write_text('﻿ id , name \nA,"a, b"\n\nA,dup\n,x\nB,"l1\nl2"\nC\n', encoding="utf-8")
    header, rows = read_csv(p, ["id"])
    errors = []
    kept = rows_by_id(header, rows, "id", "t", errors)
    assert kept == [(1, {"id": "A", "name": "a, b"}), (4, {"id": "B", "name": "l1\nl2"})]
    assert [(e["row"], e["error"]) for e in errors] == [
        (2, "duplicate_id"), (3, "missing_id"), (5, "malformed_row")]


def test_failed_write_keeps_old_file(cwd):
    out = cwd / "output/o.json"
    atomic_write_json(out, [1])
    out.write_text("OLD")
    with pytest.raises(TypeError):
        atomic_write_json(out, [object()])
    assert out.read_text() == "OLD"
    assert [p.name for p in out.parent.iterdir()] == ["o.json"]
```

---

## Recap

1. Decide the **status-code order** up front: 503, 400, 404, 422, then 200.
2. **Resolve paths, then check containment.** Never check the path string.
3. Read CSVs with `utf-8-sig` and the `csv` module, **by header name**, counting rows as parsed records.
4. **Collect per-row errors,** and decide per rule whether to skip or keep with a null.
5. **Write atomically:** temp file in the same folder, `fsync`, then `os.replace`.
6. **Cache by content hash** so re-runs only redo what changed or failed.

*Next: four FastAPI building blocks for production.*

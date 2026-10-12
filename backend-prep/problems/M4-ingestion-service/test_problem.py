import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from problem_api import SAMPLE_JSONL, RetryableError, flaky_classifier, keyword_label

TIMEOUT_S = 5.0


# ------------------------------------------------------------------ helpers


@contextmanager
def service(sol, store, classifier=None):
    with TestClient(sol.create_app(store, classifier)) as client:
        yield client


def jsonl(*objs) -> bytes:
    return "".join((o if isinstance(o, str) else json.dumps(o)) + "\n" for o in objs).encode()


def rows_of(*texts):
    return [{"id": f"r{i}", "text": t} for i, t in enumerate(texts, start=1)]


def upload(client, raw: bytes):
    return client.post("/batches", files={"file": ("rows.jsonl", raw, "application/x-ndjson")})


def new_batch(client, *texts) -> str:
    resp = upload(client, jsonl(*rows_of(*texts)))
    assert resp.status_code == 201, resp.text
    return resp.json()["batch_id"]


def wait_until(fn, what: str, timeout: float = TIMEOUT_S):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.005)
    raise AssertionError(f"timed out after {timeout}s waiting for {what}")


def wait_job(client, job_id: str) -> dict:
    def done():
        job = client.get(f"/jobs/{job_id}").json()
        return job if job.get("status") == "completed" else None
    return wait_until(done, f"job {job_id} to complete")


def process(client, batch_id: str) -> dict:
    resp = client.post(f"/batches/{batch_id}/process")
    assert resp.status_code == 202, f"expected 202, got {resp.status_code}: {resp.text}"
    return resp.json()


class Gate:
    """A classifier that blocks until .open() is called (or 2 s pass)."""

    def __init__(self):
        self.event = threading.Event()
        self.calls: list[str] = []
        self.waiting = threading.Event()

    def __call__(self, text):
        self.calls.append(text)
        self.waiting.set()
        self.event.wait(2.0)
        return "ok"

    def open(self):
        self.event.set()


class Crash(SystemExit):
    """Simulates the process dying (a BaseException: don't catch it)."""


class Crasher:
    """Labels the first `ok_calls` rows 'before', then kills the worker thread."""

    def __init__(self, ok_calls: int):
        self.ok_calls = ok_calls
        self.calls: list[str] = []
        self.thread: threading.Thread | None = None
        self.died = threading.Event()

    def __call__(self, text):
        self.calls.append(text)
        if len(self.calls) > self.ok_calls:
            self.thread = threading.current_thread()
            self.died.set()
            raise Crash()
        return "before"

    def wait_dead(self):
        assert self.died.wait(TIMEOUT_S), "the worker never reached the crash"
        self.thread.join(TIMEOUT_S)
        assert not self.thread.is_alive(), "the crash must propagate and end the worker thread"


class Recorder:
    def __init__(self, label="after"):
        self.label = label
        self.calls: list[str] = []
        self.lock = threading.Lock()

    def __call__(self, text):
        with self.lock:
            self.calls.append(text)
        return self.label


# ------------------------------------------------------------------ part 1


def test_part1_upload_valid_batch(sol, tmp_path):
    """POST /batches with valid JSONL -> 201 with counts; GET /batches/{id} shows all rows pending"""
    with service(sol, tmp_path / "store") as client:
        resp = upload(client, jsonl(*rows_of("a", "b", "c")))
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert (body["accepted"], body["rejected"], body["errors"]) == (3, 0, [])
        batch = client.get(f"/batches/{body['batch_id']}").json()
        assert batch == {"batch_id": body["batch_id"], "row_count": 3,
                         "counts": {"pending": 3, "done": 0, "failed": 0}}


def test_part1_sample_file_errors(sol, tmp_path):
    """The sample upload: 5 accepted and each bad line reported with its line number and first error"""
    with service(sol, tmp_path / "store") as client:
        body = upload(client, SAMPLE_JSONL.read_bytes()).json()
        assert (body["accepted"], body["rejected"]) == (5, 5)
        assert body["errors"] == [{"line": 5, "error": "missing_text"}, {"line": 6, "error": "duplicate_id"},
                                  {"line": 7, "error": "missing_id"}, {"line": 8, "error": "not_an_object"},
                                  {"line": 10, "error": "invalid_json"}]


def test_part1_validation_order(sol, tmp_path):
    """Checks run in order: a non-string id is missing_id; a non-string text is missing_text; first dup wins"""
    raw = jsonl({"id": 7, "text": "x"}, {"id": "", "text": "x"}, {"id": "a", "text": 5}, {"id": "a", "text": "kept"},
                {"id": "a", "text": "dup"}, "null", "  ", "{nope")
    with service(sol, tmp_path / "store") as client:
        body = upload(client, raw).json()
        assert [(e["line"], e["error"]) for e in body["errors"]] == [
            (1, "missing_id"), (2, "missing_id"), (3, "missing_text"), (5, "duplicate_id"), (6, "not_an_object"),
            (8, "invalid_json")]
        rows = client.get(f"/batches/{body['batch_id']}/rows").json()["rows"]
        assert [r["text"] for r in rows] == ["kept"]


def test_part1_rows_listing(sol, tmp_path):
    """GET /batches/{id}/rows lists rows in upload order with the initial fields; CRLF and unicode are fine"""
    raw = b'{"id": "z", "text": "first \\u00e9t\\u00e9"}\r\n{"id": "a", "text": "second \xe2\x9c\x93"}\r\n'
    with service(sol, tmp_path / "store") as client:
        batch_id = upload(client, raw).json()["batch_id"]
        rows = client.get(f"/batches/{batch_id}/rows").json()["rows"]
        assert rows == [
            {"id": "z", "text": "first été", "status": "pending", "label": None, "attempts": 0, "error": None},
            {"id": "a", "text": "second ✓", "status": "pending", "label": None, "attempts": 0, "error": None}]


def test_part1_rejects_unusable_files(sol, tmp_path):
    """No valid rows -> 422 with the errors; bytes that aren't UTF-8 -> 400"""
    with service(sol, tmp_path / "store") as client:
        resp = upload(client, jsonl({"text": "no id"}, "[]"))
        assert resp.status_code == 422
        assert resp.json()["errors"] == [{"line": 1, "error": "missing_id"}, {"line": 2, "error": "not_an_object"}]
        assert upload(client, b'{"id": "a", "text": "\xff\xfe"}\n').status_code == 400


def test_part1_unknown_ids_are_404(sol, tmp_path):
    """Unknown batch ids are 404 on both GET endpoints"""
    with service(sol, tmp_path / "store") as client:
        for path in ("/batches/b_nope", "/batches/b_nope/rows"):
            resp = client.get(path)
            assert resp.status_code == 404 and resp.json() == {"detail": "batch not found"}


def test_part1_stored_in_sqlite(sol, tmp_path):
    """Batches live in an SQLite file under storage_dir: a new app over the same dir sees them"""
    store = tmp_path / "store"
    with service(sol, store) as client:
        batch_id = new_batch(client, "a", "b")
    files = [p for p in store.rglob("*") if p.is_file()]
    assert any(p.read_bytes()[:16] == b"SQLite format 3\x00" for p in files), "use an SQLite database in storage_dir"
    with service(sol, store) as client:
        assert client.get(f"/batches/{batch_id}").json()["row_count"] == 2


# ------------------------------------------------------------------ part 2


def test_part2_process_labels_every_row(sol, tmp_path):
    """POST /process -> 202 queued; the worker labels every row and the job completes with counts"""
    with service(sol, tmp_path / "store", flaky_classifier()) as client:
        batch_id = new_batch(client, "Love it", "It arrived broken", "meh")
        job = process(client, batch_id)
        assert job["status"] == "queued" and job["job_id"]
        final = wait_job(client, job["job_id"])
        assert final == {"job_id": job["job_id"], "batch_id": batch_id, "status": "completed",
                         "total": 3, "done": 3, "failed": 0}
        rows = client.get(f"/batches/{batch_id}/rows").json()["rows"]
        assert [(r["status"], r["label"], r["attempts"]) for r in rows] == [
            ("done", "positive", 1), ("done", "negative", 1), ("done", "neutral", 1)]
        assert client.get(f"/batches/{batch_id}").json()["counts"] == {"pending": 0, "done": 3, "failed": 0}


def test_part2_runs_in_background_with_progress(sol, tmp_path):
    """The request returns before classification; GET /jobs shows running progress, then completed"""
    gate = Gate()
    with service(sol, tmp_path / "store", gate) as client:
        batch_id = new_batch(client, "one", "two")
        job = process(client, batch_id)
        assert gate.waiting.wait(TIMEOUT_S), "the worker never called the classifier"
        running = client.get(f"/jobs/{job['job_id']}").json()
        assert running["status"] == "running" and running["done"] == 0 and running["total"] == 2, \
            "classification must happen in a background thread, not inside the request"
        gate.open()
        assert wait_job(client, job["job_id"])["done"] == 2


def test_part2_retryable_errors(sol, tmp_path):
    """RetryableError is retried up to 3 attempts in total; the last error is kept if all fail"""
    with service(sol, tmp_path / "store", flaky_classifier(fail_first=2)) as client:
        batch_id = new_batch(client, "[flaky] Love it")
        wait_job(client, process(client, batch_id)["job_id"])
        row = client.get(f"/batches/{batch_id}/rows").json()["rows"][0]
        assert (row["status"], row["label"], row["attempts"], row["error"]) == ("done", "positive", 3, None)
    with service(sol, tmp_path / "store2", flaky_classifier(fail_first=5)) as client:
        batch_id = new_batch(client, "[flaky] Love it")
        job = wait_job(client, process(client, batch_id)["job_id"])
        row = client.get(f"/batches/{batch_id}/rows").json()["rows"][0]
        assert (row["status"], row["label"], row["attempts"]) == ("failed", None, 3)
        assert row["error"] == "model overloaded (attempt 3)"
        assert (job["done"], job["failed"]) == (0, 1)


def test_part2_permanent_errors_do_not_stop_the_job(sol, tmp_path):
    """A non-retryable error fails that row after 1 attempt; the other rows are still labeled"""
    clf = flaky_classifier()
    with service(sol, tmp_path / "store", clf) as client:
        batch_id = new_batch(client, "Great", "[bad] junk", "It broke, terrible")
        job = wait_job(client, process(client, batch_id)["job_id"])
        assert (job["done"], job["failed"]) == (2, 1)
        rows = client.get(f"/batches/{batch_id}/rows").json()["rows"]
        assert rows[1] == {"id": "r2", "text": "[bad] junk", "status": "failed", "label": None,
                           "attempts": 1, "error": "unclassifiable input"}
        assert clf.calls.count("[bad] junk") == 1, "permanent errors are not retried"


def test_part2_jobs_run_in_creation_order(sol, tmp_path):
    """Jobs run one at a time in creation order, rows in upload order"""
    rec = Recorder()
    with service(sol, tmp_path / "store", rec) as client:
        a = new_batch(client, "a1", "a2", "a3")
        b = new_batch(client, "b1", "b2")
        ja, jb = process(client, a)["job_id"], process(client, b)["job_id"]
        wait_job(client, ja)
        wait_job(client, jb)
    assert rec.calls == ["a1", "a2", "a3", "b1", "b2"]


def test_part2_unknown_batch_or_job(sol, tmp_path):
    """Processing an unknown batch and polling an unknown job are 404"""
    with service(sol, tmp_path / "store", Recorder()) as client:
        resp = client.post("/batches/b_nope/process")
        assert resp.status_code == 404 and resp.json() == {"detail": "batch not found"}
        resp = client.get("/jobs/j_nope")
        assert resp.status_code == 404 and resp.json() == {"detail": "job not found"}


# ------------------------------------------------------------------ part 3


def test_part3_restart_keeps_everything(sol, tmp_path):
    """A new app over the same directory sees finished batches, rows and jobs unchanged"""
    store = tmp_path / "store"
    with service(sol, store, flaky_classifier()) as client:
        batch_id = new_batch(client, "Love it", "[bad] x")
        job = wait_job(client, process(client, batch_id)["job_id"])
        rows = client.get(f"/batches/{batch_id}/rows").json()
    with service(sol, store, Recorder()) as client:
        assert client.get(f"/jobs/{job['job_id']}").json() == job
        assert client.get(f"/batches/{batch_id}/rows").json() == rows


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_part3_crash_mid_job_resumes_same_job(sol, tmp_path):
    """After a crash mid-job, the next app resumes the same job and classifies only the pending rows"""
    store = tmp_path / "store"
    crasher = Crasher(ok_calls=2)
    with service(sol, store, crasher) as client:
        batch_id = new_batch(client, "t1", "t2", "t3", "t4", "t5")
        job_id = process(client, batch_id)["job_id"]
        crasher.wait_dead()
    rec = Recorder()
    with service(sol, store, rec) as client:
        job = wait_job(client, job_id)
        assert (job["total"], job["done"], job["failed"]) == (5, 5, 0)
        labels = [r["label"] for r in client.get(f"/batches/{batch_id}/rows").json()["rows"]]
    assert labels == ["before", "before", "after", "after", "after"]
    assert rec.calls == ["t3", "t4", "t5"], "rows already done must never be classified again"


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_part3_queued_jobs_resume_in_order(sol, tmp_path):
    """Jobs that were still queued at the crash are resumed too, after the interrupted one"""
    store = tmp_path / "store"
    crasher = Crasher(ok_calls=1)
    with service(sol, store, crasher) as client:
        a = new_batch(client, "a1", "a2")
        b = new_batch(client, "b1")
        ja, jb = process(client, a)["job_id"], process(client, b)["job_id"]
        crasher.wait_dead()
        assert client.get(f"/jobs/{jb}").json()["status"] == "queued"
    rec = Recorder()
    with service(sol, store, rec) as client:
        wait_job(client, ja)
        wait_job(client, jb)
    assert rec.calls == ["a2", "b1"]


def test_part3_reprocess_is_idempotent(sol, tmp_path):
    """Processing a fully processed batch again -> 200 nothing_to_do and no classifier calls"""
    rec = Recorder()
    with service(sol, tmp_path / "store", rec) as client:
        batch_id = new_batch(client, "a", "b")
        wait_job(client, process(client, batch_id)["job_id"])
        resp = client.post(f"/batches/{batch_id}/process")
        assert resp.status_code == 200
        assert resp.json() == {"job_id": None, "status": "nothing_to_do"}
    assert rec.calls == ["a", "b"]


def test_part3_concurrent_process_requests_make_one_job(sol, tmp_path):
    """Concurrent identical process requests: exactly one 202, every response has the same job_id"""
    gate = Gate()
    with service(sol, tmp_path / "store", gate) as client:
        batch_id = new_batch(client, "a", "b")
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: client.post(f"/batches/{batch_id}/process"), range(8)))
        statuses = sorted(r.status_code for r in responses)
        assert statuses == [200] * 7 + [202], f"expected one 202 and seven 200s, got {statuses}"
        assert len({r.json()["job_id"] for r in responses}) == 1
        again = client.post(f"/batches/{batch_id}/process")
        assert again.status_code == 200 and again.json()["job_id"] == responses[0].json()["job_id"]
        gate.open()
        wait_job(client, responses[0].json()["job_id"])
    assert sorted(gate.calls) == ["a", "b"], "each row classified once"


def test_part3_no_5xx_under_concurrency(sol, tmp_path):
    """Concurrent uploads, process calls and polls while the worker writes: never a 5xx"""
    with service(sol, tmp_path / "store", keyword_label) as client:
        def work(i):
            codes = []
            r = upload(client, jsonl(*rows_of(*[f"text {i}-{k} great" for k in range(5)])))
            codes.append(r.status_code)
            batch_id = r.json()["batch_id"]
            p = client.post(f"/batches/{batch_id}/process")
            codes.append(p.status_code)
            for _ in range(5):
                codes.append(client.get(f"/batches/{batch_id}").status_code)
                codes.append(client.get(f"/jobs/{p.json()['job_id']}").status_code)
            return codes, p.json()["job_id"]

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(work, range(12)))
        codes = [c for cs, _ in results for c in cs]
        assert all(c < 500 for c in codes), f"server errors under concurrency: {sorted(set(codes))}"
        for _, job_id in results:
            assert wait_job(client, job_id)["done"] == 5

"""Tests use real threads. Nothing sleeps for long: blocking jobs wait on threading.Events
the test releases, and polling gives up after ~5 s so a broken solution fails instead of hanging."""

import threading
import time
import warnings

warnings.filterwarnings("ignore", message="Using `httpx`")  # starlette TestClient notice
from fastapi.testclient import TestClient  # noqa: E402

TIMEOUT_S = 5.0


def wait_until(predicate, what, timeout=TIMEOUT_S):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.005)
    raise AssertionError(f"timed out after {timeout}s waiting for {what}")


def submit(c, body):
    resp = c.post("/jobs", json=body)
    assert resp.status_code == 202, f"POST /jobs should be 202, got {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert data["status"] == "queued" and isinstance(data["job_id"], str), f"bad POST body: {data}"
    return data["job_id"]


def job(c, job_id):
    resp = c.get(f"/jobs/{job_id}")
    assert resp.status_code == 200, f"GET /jobs/{job_id} should be 200, got {resp.status_code}"
    return resp.json()


def wait_finished(c, job_id):
    return wait_until(lambda: (j := job(c, job_id))["status"] in ("done", "failed") and j,
                      f"job {job_id} to finish")


def listed(c, status=None):
    resp = c.get("/jobs", params={"status": status} if status else None)
    assert resp.status_code == 200, f"GET /jobs should be 200, got {resp.status_code}"
    return resp.json()["jobs"]


class Gate:
    """A `process` that blocks until released, recording who started it and in which thread."""

    def __init__(self, result="ok"):
        self.release = threading.Event()
        self.result = result
        self.started = []  # payloads, in start order
        self.threads = []
        self._lock = threading.Lock()

    def __call__(self, payload):
        with self._lock:
            self.started.append(payload)
            self.threads.append(threading.current_thread())
        self.release.wait(TIMEOUT_S)
        return self.result


def test_word_count_and_sum(sol):
    """The default processor: word_count counts words, sum adds numbers; results show as done"""
    with TestClient(sol.create_app()) as c:
        wc = submit(c, {"kind": "word_count", "text": "the quick  brown\nfox"})
        sm = submit(c, {"kind": "sum", "numbers": [1, 2, 3.5]})
        assert wait_finished(c, wc) == {"job_id": wc, "kind": "word_count", "status": "done",
                                        "result": 4, "error": None}
        assert wait_finished(c, sm) == {"job_id": sm, "kind": "sum", "status": "done",
                                        "result": 6.5, "error": None}


def test_default_processor_rejects_bad_input(sol):
    """Bad input to the default processor makes the job failed with an error message, result null"""
    with TestClient(sol.create_app()) as c:
        ids = [submit(c, b) for b in ({"kind": "word_count"}, {"kind": "word_count", "text": 42},
                                      {"kind": "sum", "numbers": "1,2"}, {"kind": "sum", "numbers": [1, "2"]})]
        for job_id in ids:
            j = wait_finished(c, job_id)
            assert j["status"] == "failed", f"{j} should have failed"
            assert isinstance(j["error"], str) and j["error"], "error must be a non-empty message"
            assert j["result"] is None


def test_post_does_not_wait_and_running_is_visible(sol):
    """POST returns 202 while the job is still blocked; GET shows running, then done with the result"""
    gate = Gate(result={"score": 0.93})
    with TestClient(sol.create_app(workers=1, process=gate)) as c:
        try:
            job_id = submit(c, {"kind": "word_count", "text": "slow"})
            wait_until(lambda: gate.started, "the worker to pick up the job")
            assert job(c, job_id)["status"] == "running", "status must be running while process() runs"
            assert [j["job_id"] for j in listed(c, "running")] == [job_id]
        finally:
            gate.release.set()
        assert wait_finished(c, job_id) == {"job_id": job_id, "kind": "word_count", "status": "done",
                                            "result": {"score": 0.93}, "error": None}
        assert gate.started == [{"kind": "word_count", "text": "slow"}], \
            "process() must receive the whole posted object"


def test_failure_does_not_kill_worker(sol):
    """A raising process marks the job failed with str(exc) (class name if empty); the worker keeps going"""
    def process(payload):
        if payload.get("text") == "boom":
            raise ValueError("boom: bad input")
        if payload.get("text") == "silent":
            raise RuntimeError()
        return "fine"

    with TestClient(sol.create_app(workers=1, process=process)) as c:
        bad = submit(c, {"kind": "word_count", "text": "boom"})
        silent = submit(c, {"kind": "word_count", "text": "silent"})
        good = submit(c, {"kind": "word_count", "text": "ok"})
        assert wait_finished(c, bad) == {"job_id": bad, "kind": "word_count", "status": "failed",
                                         "result": None, "error": "boom: bad input"}
        assert wait_finished(c, silent)["error"] == "RuntimeError", "empty str(exc) -> the class name"
        assert wait_finished(c, good)["status"] == "done", "the only worker died after a failing job"


def test_worker_count_limits_concurrency(sol):
    """With workers=2, two jobs run at once and the third stays queued until one is released"""
    gate = Gate()
    with TestClient(sol.create_app(workers=2, process=gate)) as c:
        try:
            ids = [submit(c, {"kind": "sum", "numbers": [i]}) for i in range(3)]
            wait_until(lambda: len(gate.started) == 2, "two workers to start jobs")
            time.sleep(0.05)  # give a (wrong) third worker a chance to show up
            assert len(gate.started) == 2, f"{len(gate.started)} jobs running with workers=2"
            assert [j["job_id"] for j in listed(c, "running")] == ids[:2], "the first two jobs should run"
            assert [j["job_id"] for j in listed(c, "queued")] == ids[2:], "the third job should still be queued"
            assert len({t.ident for t in gate.threads}) == 2, "the two running jobs must be on different threads"
        finally:
            gate.release.set()
        for job_id in ids:
            wait_finished(c, job_id)
        assert [j["job_id"] for j in listed(c, "done")] == ids


def test_fifo_with_one_worker(sol):
    """With one worker, jobs run in submission order"""
    order = []

    def process(payload):
        order.append(payload["numbers"][0])
        return payload["numbers"][0]

    with TestClient(sol.create_app(workers=1, process=process)) as c:
        ids = [submit(c, {"kind": "sum", "numbers": [i]}) for i in range(8)]
        for job_id in ids:
            wait_finished(c, job_id)
    assert order == list(range(8)), f"jobs ran out of order: {order}"


def test_list_all_in_submission_order(sol):
    """GET /jobs with no filter lists every job, in submission order, in the same shape as GET /jobs/{id}"""
    with TestClient(sol.create_app(workers=2)) as c:
        ids = [submit(c, {"kind": "sum", "numbers": [i, i]}) for i in range(5)]
        for job_id in ids:
            wait_finished(c, job_id)
        jobs = listed(c)
        assert [j["job_id"] for j in jobs] == ids
        assert jobs == [job(c, i) for i in ids]
        assert [j["result"] for j in jobs] == [0, 2, 4, 6, 8]
        assert listed(c, "failed") == []


def test_errors(sol):
    """Unknown job is 404; unknown kind, non-object body and unknown status filter are 422"""
    with TestClient(sol.create_app()) as c:
        assert c.get("/jobs/nope").status_code == 404
        assert c.post("/jobs", json={"kind": "resize"}).status_code == 422, "unknown kind must be 422"
        assert c.post("/jobs", json={"text": "no kind"}).status_code == 422, "missing kind must be 422"
        assert c.post("/jobs", json=["word_count"]).status_code == 422, "a non-object body must be 422"
        assert c.get("/jobs", params={"status": "sleeping"}).status_code == 422
        assert listed(c) == [], "rejected submissions must not create jobs"


def test_shutdown_stops_workers(sol):
    """Leaving the app's lifespan stops and joins every worker thread"""
    gate = Gate()
    with TestClient(sol.create_app(workers=2, process=gate)) as c:
        ids = [submit(c, {"kind": "sum", "numbers": [i]}) for i in range(2)]
        wait_until(lambda: len(gate.started) == 2, "both workers to start a job")
        gate.release.set()
        for job_id in ids:
            wait_finished(c, job_id)
    for t in gate.threads:
        t.join(timeout=2)
    alive = [t.name for t in gate.threads if t.is_alive()]
    assert not alive, f"worker threads still running after shutdown: {alive}"

"""Part 3: 2,000 rows, bounded concurrency, order, checkpoint/resume."""

import csv
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from conftest import CATS, OK, SCRIPT, SOLUTION_DIR, convert


def large(client):
    return convert(client, tasks="data/tasks_large.csv", output="output/large.json")


def expected_large():
    with open("data/tasks_large.csv", encoding="utf-8") as f:
        return [(r["task_id"], CATS[int(r["task_id"][1:]) % 5]) for r in csv.DictReader(f)]


def got_large():
    return [(r["task_id"], r["category"]) for r in json.loads(Path("output/large.json").read_text())]


def test_large_order_and_categories(client):
    r = large(client)
    assert r.status_code == 200, r.text
    assert r.json()["rows_written"] == 2000
    assert got_large() == expected_large()


def test_bounded_parallelism(client, llm):
    llm.delay = 0.02
    t0 = time.monotonic()
    assert large(client).status_code == 200
    elapsed = time.monotonic() - t0
    assert llm.peak <= 10, f"{llm.peak} requests in flight at once (max 10)"
    assert llm.peak >= 5, f"only {llm.peak} in flight at once: calls are not running in parallel"
    assert elapsed < 20, f"took {elapsed:.1f}s; sequential would be ~40s"


def test_rerun_makes_no_calls(client, llm):
    large(client)
    llm.reset_counts()
    assert large(client).status_code == 200
    assert llm.count(None) == 0
    assert got_large() == expected_large()


def test_changed_row_is_reclassified(client, llm, workdir):
    large(client)
    path = workdir / "data" / "tasks_large.csv"
    text = path.read_text(encoding="utf-8").replace("LRG-0007 work item", "LRG-0008 work item edited", 1)
    path.write_text(text, encoding="utf-8")
    llm.reset_counts()
    large(client)
    assert llm.count(None) == 1
    assert dict(got_large())["L0007"] == CATS[8 % 5]


def test_fallback_rows_are_not_checkpointed(client, llm):
    convert(client)
    fixed = dict(SCRIPT)
    fixed["Benchmark reasoning model"] = [OK("model_evaluation")]
    fixed["Audit label quality"] = [OK("data_labeling")]
    fixed["Classify ticket 5531"] = [OK("other")]
    llm.set_script(fixed)
    llm.reset_counts()
    r = convert(client)
    assert llm.count(None) == 3  # only the three rows that fell back last time
    cats = {x["task_id"]: x["category"] for x in json.loads(Path("output/tasks.json").read_text())}
    assert (cats["T011"], cats["T013"], cats["T010"]) == ("model_evaluation", "data_labeling", "other")
    assert not [e for e in r.json()["errors"] if e["error"] == "classification_failed"]


# ---------------------------------------------------------------- real kill


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(workdir, port):
    env = dict(os.environ, PYTHONPATH=str(SOLUTION_DIR))
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level",
                             "warning"], cwd=workdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            httpx.get(f"http://127.0.0.1:{port}/docs", timeout=0.2)
            return proc
        except httpx.HTTPError:
            time.sleep(0.1)
    proc.kill()
    pytest.fail("uvicorn app.main:app did not start")


def test_resume_after_kill(workdir, llm):
    llm.delay = 0.01
    body = {"tasks_path": "data/tasks_large.csv", "users_path": "data/users.csv", "output_path": "output/large.json"}
    port = _free_port()
    proc = _serve(workdir, port)
    t = threading.Thread(target=lambda: _quiet_post(port, body), daemon=True)
    t.start()
    deadline = time.monotonic() + 30
    while llm.count(None) < 600 and time.monotonic() < deadline:
        time.sleep(0.005)
    proc.kill()  # SIGKILL: no cleanup handlers run
    proc.wait()
    killed_at = llm.count(None)
    assert 600 <= killed_at < 2000, f"kill landed at {killed_at} calls"
    assert not (workdir / "output" / "large.json").exists() or json.loads((workdir / "output" / "large.json").read_text())

    llm.reset_counts()
    port = _free_port()
    proc = _serve(workdir, port)
    try:
        r = httpx.post(f"http://127.0.0.1:{port}/convert", json=body, timeout=60)
    finally:
        proc.kill()
        proc.wait()
    assert r.status_code == 200, r.text
    assert got_large() == expected_large()
    second = llm.count(None)
    assert second <= 2000 - killed_at + 60, (
        f"first run made {killed_at} calls before the kill, but the resumed run made {second} (expected about "
        f"{2000 - killed_at}); checkpoint at least every 50 completed rows")


def _quiet_post(port, body):
    try:
        httpx.post(f"http://127.0.0.1:{port}/convert", json=body, timeout=60)
    except httpx.HTTPError:
        pass

import json
import shutil
from pathlib import Path

import httpx

from dispatcher.__main__ import main
from mock_services.clock import FakeClock
from mock_services.webhooks import WebhookReceiver

DATA = Path(__file__).resolve().parents[3] / "candidate" / "data"


def run(tmp_path, capsys, receiver, clock):
    argv = ["run", "--once", "--state-dir", str(tmp_path / "state"), "--events", str(tmp_path / "events.jsonl"),
            "--subscriptions", str(tmp_path / "subscriptions.json")]
    code = main(argv, http=httpx.Client(transport=receiver.transport()), clock=clock)
    return code, json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_run_once_over_sample_data_twice(tmp_path, capsys):
    shutil.copy(DATA / "events.jsonl", tmp_path)
    shutil.copy(DATA / "subscriptions.json", tmp_path)
    clock = FakeClock()
    receiver = WebhookReceiver(clock=clock)
    code, report = run(tmp_path, capsys, receiver, clock)
    # 6 valid events -> warehouse 6, qa_bot 3 (2 completed + 1 failed), exports 2
    assert code == 0 and report == {"attempted": 11, "delivered": 11, "failed": 0, "dead": 0,
                                    "skipped_lines": [3, 7, 8, 9, 11]}
    code, report = run(tmp_path, capsys, receiver, clock)
    assert report["attempted"] == 0 and len(receiver.deliveries) == 11


def test_bad_subscriptions_exit_2(tmp_path, capsys):
    (tmp_path / "subscriptions.json").write_text('[{"id": "x"}]')
    code = main(["run", "--once", "--state-dir", str(tmp_path), "--events", str(tmp_path / "e.jsonl"),
                 "--subscriptions", str(tmp_path / "subscriptions.json")])
    assert code == 2 and "'url' must be an http(s) URL" in capsys.readouterr().err


def test_corrupt_state_exit_2(tmp_path, capsys):
    shutil.copy(DATA / "subscriptions.json", tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "deliveries.json").write_text("{")
    code = main(["run", "--once", "--state-dir", str(tmp_path / "state"), "--events", str(tmp_path / "e.jsonl"),
                 "--subscriptions", str(tmp_path / "subscriptions.json")],
                http=httpx.Client(transport=WebhookReceiver().transport()))
    assert code == 2 and "cannot load delivery state" in capsys.readouterr().err

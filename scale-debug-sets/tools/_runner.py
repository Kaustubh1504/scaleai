"""Run a repo's unittest suite and print one JSON line with per-test results.

Invoked by common.run_tests in a subprocess:  python _runner.py <repo_root>
"""
from __future__ import annotations

import json
import sys
import time
import unittest


class RecordingResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.records: dict[str, dict] = {}
        self._start = 0.0

    def startTest(self, test):
        super().startTest(test)
        self._start = time.perf_counter()

    def _record(self, test, status, err=None):
        rec = {"status": status, "duration": round(time.perf_counter() - self._start, 4)}
        if err is not None:
            exc_type, exc, _ = err
            rec["message"] = f"{exc_type.__name__}: {exc}"
            rec["trace"] = self._exc_info_to_string(err, test)[-3000:]
        self.records[test.id()] = rec

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "fail", err)

    def addError(self, test, err):
        super().addError(test, err)
        # setUpClass errors arrive with a placeholder "test"
        self._record(test, "error", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "skip")


def main() -> int:
    repo = sys.argv[1]
    sys.path.insert(0, repo)
    suite = unittest.defaultTestLoader.discover(start_dir=f"{repo}/tests", top_level_dir=repo)
    result = RecordingResult()
    suite.run(result)
    print(json.dumps({"tests": result.records, "total": result.testsRun}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

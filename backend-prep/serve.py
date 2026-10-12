#!/usr/bin/env python3
"""Local LeetCode-style web UI.

    ../.venv/bin/python serve.py            # http://127.0.0.1:8765
    ../.venv/bin/python serve.py --port 9000 --no-browser

Your code lives in workspace/<problem>.py: edit it here or in your editor,
whichever you like (the page reloads it when you switch problems).
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import debug
import judge

UI = judge.ROOT / "ui" / "index.html"
CARDS = judge.ROOT / "flashcards" / "cards.json"
_run_lock = threading.Lock()  # one judge run at a time keeps the laptop responsive


def split_parts(md: str) -> list[str]:
    """Split a statement on <!-- part N --> markers into [intro+part1, part2, part3...]."""
    return [chunk.strip() for chunk in re.split(r"^\s*<!--\s*part\s+\d+\s*-->\s*$", md, flags=re.M | re.I)]


class Handler(BaseHTTPRequestHandler):
    server_version = "backend-prep/1.0"

    def log_message(self, fmt: str, *args) -> None:  # quieter console
        if "/api/" in (args[0] if args else ""):
            return
        super().log_message(fmt, *args)

    # ------------------------------------------------------------ helpers

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status: int = 200) -> None:
        self._send(status, json.dumps(data).encode(), "application/json")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length))

    def _problem(self, pid: str) -> dict | None:
        try:
            return judge.find(pid)
        except LookupError:
            self._json({"detail": f"no problem {pid}"}, 404)
            return None

    # ------------------------------------------------------------- routes

    def do_GET(self) -> None:
        if self.path.startswith("/api/debug/"):
            return self._debug("GET")
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self._send(200, UI.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/problems":
            progress = judge.load_progress()
            items = [{k: m[k] for k in ("id", "title", "group", "level", "minutes", "tags", "parts", "dir")}
                     | {"daily": m.get("daily", False), "progress": progress.get(m["id"]),
                        "tests_mode": judge.has_tests_mode(m)}
                     for m in judge.all_problems()]
            return self._json(items)
        if path == "/api/flashcards":
            cards = json.loads(CARDS.read_text()) if CARDS.exists() else []
            return self._json(cards)
        m = re.fullmatch(r"/api/problems/([^/]+)(/solution|/tests/solution)?", path)
        if m:
            meta = self._problem(m.group(1))
            if meta is None:
                return
            if m.group(2) == "/solution":
                return self._json({"code": judge.reference(meta)})
            if m.group(2) == "/tests/solution":
                return self._json({"code": (judge.problem_dir(meta) / "test_problem.py").read_text()})
            tests_mode = judge.has_tests_mode(meta)
            md = judge.statement(meta)
            return self._json({
                "meta": meta,
                "statement": md,
                "parts": split_parts(md),
                "code": judge.workspace_file(meta).read_text(),
                "file": str(judge.workspace_file(meta).relative_to(judge.ROOT)),
                "tests_mode": tests_mode,
                "tests_code": judge.tests_file(meta).read_text() if tests_mode else None,
                "tests_file": str(judge.tests_file(meta).relative_to(judge.ROOT)) if tests_mode else None,
                "progress": judge.load_progress().get(meta["id"]),
            })
        self._json({"detail": "not found"}, 404)

    def do_PUT(self) -> None:
        if self.path.startswith("/api/debug/"):
            return self._debug("PUT")
        m = re.fullmatch(r"/api/problems/([^/]+)/code", self.path)
        if not m:
            return self._json({"detail": "not found"}, 404)
        meta = self._problem(m.group(1))
        if meta is None:
            return
        body = self._body()
        code = body.get("code")
        if not isinstance(code, str):
            return self._json({"detail": "code must be a string"}, 400)
        _save(meta, code, body.get("kind", "solution"))
        self._json({"saved": True})

    def do_POST(self) -> None:
        if self.path.startswith("/api/debug/"):
            return self._debug("POST")
        m = re.fullmatch(r"/api/problems/([^/]+)/(run|submit|reset|tests/run|tests/submit|tests/reset)", self.path)
        if not m:
            return self._json({"detail": "not found"}, 404)
        meta = self._problem(m.group(1))
        if meta is None:
            return
        action = m.group(2)
        if action.startswith("tests/"):
            return self._tests_action(meta, action.split("/", 1)[1])
        if action == "reset":
            judge.reset(meta)
            return self._json({"code": judge.workspace_file(meta).read_text()})
        code = self._body().get("code")
        if isinstance(code, str):
            _save(meta, code)
        with _run_lock:
            if action == "run":
                return self._json(judge.run_code(meta))
            result = judge.run_tests(meta)
            result["progress"] = judge.record(result)
            return self._json(result)


    def _tests_action(self, meta: dict, action: str) -> None:
        if not judge.has_tests_mode(meta):
            return self._json({"detail": "this problem has no tests mode"}, 404)
        if action == "reset":
            judge.reset_tests(meta)
            return self._json({"code": judge.tests_file(meta).read_text()})
        body = self._body()
        if isinstance(body.get("code"), str):
            _save(meta, body["code"], "tests")
        if isinstance(body.get("solution_code"), str):
            _save(meta, body["solution_code"], "solution")
        with _run_lock:
            if action == "run":
                result = judge.run_tests(meta, judge.workspace_file(meta), judge.tests_file(meta))
                result["kind"] = "tests_run"
                return self._json(result)
            result = judge.grade_tests(meta)
            result["progress"] = judge.record_tests(result)
            return self._json(result)


    # ------------------------------------------------------------- debug

    def _debug(self, verb: str) -> None:
        url = urlsplit(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if url.path == "/api/debug/sets" and verb == "GET":
            return self._json({"sets": debug.all_sets(), "weak_spots": debug.weak_spots()})
        m = re.fullmatch(r"/api/debug/sets/([\w-]+)(?:/(\w+))?", url.path)
        if not m:
            return self._json({"detail": "not found"}, 404)
        try:
            sid = debug.find(m.group(1))
        except LookupError as exc:
            return self._json({"detail": str(exc)}, 404)
        action = m.group(2) or ""
        body = self._body() if verb in ("PUT", "POST") else {}
        try:
            return self._debug_action(verb, action, sid, query, body)
        except PermissionError as exc:
            return self._json({"detail": str(exc)}, 403)
        except (FileNotFoundError, ValueError, LookupError) as exc:
            return self._json({"detail": str(exc)}, 400)

    def _debug_action(self, verb: str, action: str, sid: str, query: dict, body: dict) -> None:
        if verb == "GET" and action == "":
            info = next((s for s in debug.all_sets() if s["id"] == sid), {})
            ws = debug.workspace(sid)
            return self._json({
                **info,
                "files": debug.files(sid),
                "tests": debug.test_files(sid),
                "readme": (ws / "README.md").read_text() if (ws / "README.md").exists() else "",
                "notes": debug.read_notes(sid),
                "questions": debug.context_questions(sid),
                "workspace": str(ws.relative_to(debug.ROOT)),
            })
        if verb == "GET" and action == "file":
            return self._json({"path": query["path"], "content": debug.read_file(sid, query["path"])})
        if verb == "GET" and action == "diff":
            return self._json({"diff": debug.diff(sid)})
        if verb == "PUT" and action == "file":
            debug.write_file(sid, body["path"], body["content"])
            return self._json({"saved": True})
        if verb == "PUT" and action == "notes":
            debug.write_notes(sid, body.get("text", ""))
            return self._json({"saved": True})
        if verb == "POST":
            for path, content in (body.get("files") or {}).items():
                if not debug.is_locked(path):
                    debug.write_file(sid, path, content)
            if action == "reset":
                debug.reset(sid)
                return self._json({"files": debug.files(sid)})
            if action == "hint":
                return self._json(debug.hint(sid))
            if action == "reveal":
                return self._json(debug.answer_key(sid))
            with _run_lock:
                if action == "main":
                    return self._json(debug.run_main(sid))
                if action == "test":
                    result = debug.run_tests(sid, body.get("test"))
                    result["progress"] = debug.record(result, body.get("elapsed_s"))
                    return self._json(result)
        return self._json({"detail": "not found"}, 404)


def _save(meta: dict, code: str, kind: str = "solution") -> None:
    path = judge.tests_file(meta) if kind == "tests" else judge.workspace_file(meta)
    tmp = path.with_suffix(".py.tmp")
    tmp.write_text(code)
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"backend-prep running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()

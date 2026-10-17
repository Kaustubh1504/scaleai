# 09. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib + httpx

import json
import threading
import time

import httpx


def fake_http(replies, delay: float = 0.0):
    """Returns (client, stats). replies: list used one per call (the last repeats), or fn(request) -> reply.
    A reply is: int status | "timeout" | "connect_error" | dict (JSON 200) | str (an OpenAI chat
    reply whose content is that string) | httpx.Response.
    stats: {"requests": [...], "max_in_flight": n}"""
    stats = {"requests": [], "max_in_flight": 0, "in_flight": 0}
    lock = threading.Lock()

    def handler(request):
        with lock:
            n = len(stats["requests"])
            stats["requests"].append(request)
            stats["in_flight"] += 1
            stats["max_in_flight"] = max(stats["max_in_flight"], stats["in_flight"])
        try:
            time.sleep(delay)
            reply = replies(request) if callable(replies) else replies[min(n, len(replies) - 1)]
            if reply == "timeout":
                raise httpx.ReadTimeout("fake timeout", request=request)
            if reply == "connect_error":
                raise httpx.ConnectError("fake connect error", request=request)
            if isinstance(reply, httpx.Response):
                return reply
            if isinstance(reply, int):
                return httpx.Response(reply, json={"error": "fake"})
            if isinstance(reply, dict):
                return httpx.Response(200, json=reply)
            return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})
        finally:
            with lock:
                stats["in_flight"] -= 1

    return httpx.Client(transport=httpx.MockTransport(handler)), stats

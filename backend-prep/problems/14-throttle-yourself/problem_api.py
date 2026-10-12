"""Mock Annotations API for problem 14. Tests and your __main__ block both use make_api().

Rate limited with kit.FixedWindowLimiter: ``limit`` requests per ``window_s``-second window of
the clock. Every response (including 404s and 429s) carries X-RateLimit-* headers.
"""

from __future__ import annotations

from kit import FakeClock, FixedWindowLimiter, MockAPI, error_response, json_response


def make_annotations(n: int) -> dict[str, dict]:
    labels = ("cat", "dog", "bird", "none")
    return {f"ann_{i:03d}": {"id": f"ann_{i:03d}", "label": labels[i % 4], "annotator": f"usr_{i % 7:02d}"}
            for i in range(1, n + 1)}


def make_api(clock: FakeClock, *, limit: int = 5, window_s: float = 1.0, latency_s: float = 0.0,
             n_annotations: int = 60) -> MockAPI:
    """
    GET /v1/annotations/{ann_id} -> the annotation, or 404.
    api.limiter.rejected counts the 429s the server sent.
    latency_s advances the clock on every request (time passes while you wait for the server).
    """
    api = MockAPI(clock=clock, latency_s=latency_s)
    limiter = FixedWindowLimiter(clock, limit, window_s)
    annotations = make_annotations(n_annotations)
    api.limiter = limiter
    api.annotations = annotations

    @api.route("GET", "/v1/annotations/{ann_id}")
    def get_annotation(req, ann_id):
        allowed, headers = limiter.check()
        if not allowed:
            return error_response(429, "rate limit exceeded", headers)
        if ann_id not in annotations:
            return error_response(404, f"annotation {ann_id} not found", headers)
        return json_response(annotations[ann_id], headers=headers)

    return api

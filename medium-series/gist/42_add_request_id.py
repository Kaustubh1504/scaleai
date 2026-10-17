# 42. Request ID on every response and log line
# Standalone: copy this file as-is. Deps: stdlib

import logging
import uuid
from contextvars import ContextVar

request_id = ContextVar("request_id", default="-")


def add_request_id(app, logger_name: str = "app") -> logging.Logger:
    """Adds X-Request-ID middleware and returns a logger whose lines include the id."""
    class Filter(logging.Filter):
        def filter(self, record):
            record.request_id = request_id.get()
            return True

    log = logging.getLogger(logger_name)
    handler = logging.StreamHandler()
    handler.addFilter(Filter())
    handler.setFormatter(logging.Formatter("%(asctime)s [%(request_id)s] %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    @app.middleware("http")
    async def middleware(request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    return log

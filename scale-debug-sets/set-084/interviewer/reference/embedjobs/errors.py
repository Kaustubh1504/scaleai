TRANSIENT_STATUSES = {500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, reason, status=None):
        super().__init__(reason)
        self.reason = reason
        self.status = status


class TransientError(ApiError):
    """Worth retrying: the server was overloaded or briefly unavailable."""


class RateLimited(TransientError):
    def __init__(self, retry_after_s):
        super().__init__("rate_limited", 429)
        self.retry_after_s = retry_after_s


class JobFailed(ApiError):
    pass


# VERIFIED
def retry_after_seconds(headers, body):
    for key, value in (headers or {}).items():
        if key.lower() == "retry-after":
            return float(value)
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and error.get("retry_after_ms") is not None:
        return error["retry_after_ms"] / 1000
    return None


def raise_for_status(response):
    if response.status == 429:
        raise RateLimited(retry_after_seconds(response.headers, response.body))
    if response.status in TRANSIENT_STATUSES:
        raise TransientError(f"http_{response.status}", response.status)
    if response.status >= 400:
        raise ApiError(f"http_{response.status}", response.status)

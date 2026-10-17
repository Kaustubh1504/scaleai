# 14. Auth token: cache until expiry, refresh once on 401
# Standalone: copy this file as-is. Deps: stdlib

import threading
import time


def make_token_getter(fetch_token, refresh_margin: float = 30.0, clock=time.time):
    """fetch_token() -> (token, expires_in_seconds). Returns get_token(invalid=None):
    cached until `refresh_margin` s before expiry; pass the token that got a 401 as `invalid`
    to force a refresh (only one thread refreshes; others reuse the new token)."""
    state = {"token": None, "expires_at": 0.0}
    lock = threading.Lock()

    def get_token(invalid=None):
        with lock:
            stale = state["token"] is None or clock() >= state["expires_at"] - refresh_margin
            if stale or (invalid is not None and invalid == state["token"]):
                token, expires_in = fetch_token()
                state["token"], state["expires_at"] = token, clock() + float(expires_in)
            return state["token"]

    return get_token


def call_with_token(get_token, send):
    """send(token) -> httpx.Response. On 401: refresh the token and retry once."""
    token = get_token()
    r = send(token)
    if r.status_code == 401:
        r = send(get_token(invalid=token))
    return r

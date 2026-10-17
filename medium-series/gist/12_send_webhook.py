# 12. Send a signed webhook with an idempotency key
# Standalone: copy this file as-is. Deps: stdlib + httpx

import hashlib
import hmac
import json
import time

import httpx


def send_webhook(url: str, secret: str, payload: dict, idempotency_key: str, *,
                 retries: int = 2, backoff: float = 0.2, timeout: float = 5, client=None) -> bool:
    """POST signed JSON. Any 2xx -> True. Retries 429/5xx/network errors with the SAME key.
    Header: X-Signature: sha256=<hex HMAC-SHA256 of the exact body bytes>."""
    body = json.dumps(payload, separators=(",", ":")).encode()      # sign exactly what we send
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
        "X-Signature": "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
    }
    http = client or httpx.Client()
    try:
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(backoff * 2 ** (attempt - 1))
            try:
                r = http.post(url, content=body, headers=headers, timeout=timeout)
            except httpx.TransportError:
                continue
            if r.is_success:
                return True
            if r.status_code != 429 and r.status_code < 500:
                return False                      # 400/401/...: retrying won't help
        return False
    finally:
        if client is None:
            http.close()

"""HMAC signatures for outgoing webhooks.

    X-Webhook-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256(secret, "<t>." + raw body)>

Subscribers recompute the HMAC over the exact bytes they received, so sign the
same bytes you send.
"""

from __future__ import annotations

import hashlib
import hmac

SIGNATURE_HEADER = "X-Webhook-Signature"


def sign(secret: str, body: bytes, timestamp: int) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"

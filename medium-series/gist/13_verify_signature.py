# 13. Verify a webhook signature (receiver side)
# Standalone: copy this file as-is. Deps: stdlib

import hashlib
import hmac


def verify_signature(secret: str, body: bytes, header, prefix: str = "sha256=") -> bool:
    """Compare against the RAW request bytes (await request.body()), in constant time."""
    expected = prefix + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")

def should_retry(attempts, max_retries):
    """attempts = attempts made so far, including the one that just failed."""
    return attempts < max_retries


# VERIFIED
def backoff_delay(attempts, base):
    return base * attempts

# 01. Call an LLM: retries, JSON, validation, one re-ask
# Standalone: copy this file as-is. Deps: stdlib + httpx

import json
import os
import time

import httpx


def ask_llm(system: str, user: str, validate=None, json_mode: bool = True, client=None):
    """One LLM answer, or None. Never raises on API/model failure.

    validate(data: dict) -> value to return, or None if the reply is unacceptable (triggers one re-ask).
    Env, read on every call: OPENAI_API_KEY (required), OPENAI_BASE_URL, OPENAI_MODEL,
    LLM_TIMEOUT=10, LLM_BACKOFF_BASE=0.5, LLM_MAX_RETRIES=3.
    Raises RuntimeError only if the key is missing (map it to 503).
    429/5xx/timeout/connection error -> retried with backoff; other 4xx -> no retry.
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    timeout = float(os.environ.get("LLM_TIMEOUT", "10"))
    backoff = float(os.environ.get("LLM_BACKOFF_BASE", "0.5"))
    retries = int(os.environ.get("LLM_MAX_RETRIES", "3"))
    payload = {"model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), "temperature": 0,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    http = client or httpx.Client()

    def call():                                   # content str, "" if garbled, None if failed
        for attempt in range(retries + 1):
            if attempt:
                time.sleep(backoff * 2 ** (attempt - 1))
            try:
                r = http.post(url, json=payload, timeout=timeout,
                              headers={"Authorization": f"Bearer {key}"})
            except httpx.TransportError:
                continue
            if r.status_code == 429 or r.status_code >= 500:
                continue
            if r.status_code != 200:
                return None
            try:
                return r.json()["choices"][0]["message"]["content"] or ""
            except (ValueError, LookupError, TypeError):
                return ""
        return None

    try:
        for _ in range(2):                        # first try + one re-ask on bad output
            content = call()
            if content is None:                   # transport budget spent: don't re-ask
                return None
            if not json_mode:
                if content:
                    return content
                continue
            try:
                data = json.loads(content)
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            try:
                result = validate(data) if validate else data
            except Exception:
                result = None
            if result is not None:
                return result
        return None
    finally:
        if client is None:
            http.close()

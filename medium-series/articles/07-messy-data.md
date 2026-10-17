# Taming Messy API Data in Python: A Step-by-Step Guide to Normalizing JSON and Redacting PII

### Small functions that turn "null", "$1,234.50" and epoch milliseconds into clean values, and keep emails out of your logs

Real API payloads are rarely clean. The same field arrives as `12`, `"12"`, `" $12.00 "` and `null`. The email lives in `email` for some records and in `contact.email` for others. Timestamps show up as ISO strings, epoch seconds, *and* epoch milliseconds. And some of the text contains customers' phone numbers, which must not reach your logs or an LLM.

In this tutorial we'll build two standalone snippets:

1. **Normalizers:** `get_path`, `first`, `to_number`, `to_bool`, `to_datetime`
2. **A PII redactor:** `redact` and `redact_obj`

**What you need:** Python 3.9+. Standard library only.

---

## Part 1: Normalizing messy JSON

### Step 1: Read nested fields without a wall of `.get()`

The naive version crashes as soon as one level is missing:

```python
email = rec["contact"]["emails"][0]          # KeyError, IndexError, TypeError...
email = rec.get("contact", {}).get("emails", [{}])[0]   # still breaks if contact is None
```

Instead, write one function that walks a dotted path and returns a default as soon as any step is missing. Numeric parts index into lists: `"items.0.id"`.

### Step 2: Decide what "missing" means, in one place

`None`, `""`, `"null"`, `"N/A"` and `"-"` all mean "no value" in real payloads. Put that list in a single `MISSING` set, so every field is treated the same way.

### Step 3: Fall back across several fields

`first(rec, "email", "contact.email", "user.emails.0")` returns the first path that holds a real value. That one line replaces a nest of `if`/`else`.

### Step 4: Parse numbers strictly

`float(" $1,234.50 ")` raises. `float("nan")` succeeds, and NaN then poisons every sum it touches. And `True` is an `int` in Python, so `isinstance(True, int)` is true. The parser should:

- strip currency symbols, commas and spaces,
- try `int` first (so `"12"` stays an integer), then `float`,
- reject booleans, NaN and infinity.

### Step 5: Booleans and dates

- **Booleans:** accept the usual spellings (`"yes"`, `"t"`, `1`), and return `None` when unclear rather than guessing `False`.
- **Dates:** detect epoch numbers. A value above 1e11 must be milliseconds, because in seconds it would be thousands of years in the future. Accept ISO strings with a `Z` suffix, and always return a timezone-aware UTC datetime, so comparisons never mix naive and aware values.

### The complete snippet

```python
import re
from datetime import datetime, timezone

MISSING = {"", "null", "none", "n/a", "na", "-"}


def get_path(obj, path: str, default=None):
    """get_path(rec, "user.profile.email") or "items.0.id". Returns default if any step is missing."""
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list) and part.lstrip("-").isdigit() and -len(obj) <= int(part) < len(obj):
            obj = obj[int(part)]
        else:
            return default
    return obj


def clean_str(v):
    """Stripped string, or None for None / "" / "null" / "N/A" / "-"."""
    if v is None:
        return None
    s = str(v).strip()
    return None if s.lower() in MISSING else s


def first(record, *paths, convert=clean_str):
    """First path whose converted value isn't None: first(rec, "email", "contact.email")."""
    for p in paths:
        v = convert(get_path(record, p))
        if v is not None:
            return v
    return None


def to_number(v):
    """12, "12", " $1,234.50 ", "1e3" -> int/float. bools, junk, NaN, inf -> None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        n = v
    else:
        s = re.sub(r"[,\s$€£]", "", str(v))
        try:
            n = int(s)
        except ValueError:
            try:
                n = float(s)
            except ValueError:
                return None
    if isinstance(n, float) and (n != n or n in (float("inf"), float("-inf"))):
        return None
    return n


def to_bool(v):
    """True/False from bools, 0/1, "yes"/"no", "t"/"f"... None if unclear."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    s = str(v).strip().lower() if v is not None else ""
    if s in ("true", "t", "yes", "y", "1"):
        return True
    if s in ("false", "f", "no", "n", "0"):
        return False
    return None


def to_datetime(v):
    """ISO strings (with Z or offset), dates, epoch seconds or milliseconds -> aware UTC datetime, else None."""
    if v is None or isinstance(v, bool):
        return None
    s = str(v).strip()
    if isinstance(v, (int, float)) or re.fullmatch(r"\d{9,13}(\.\d+)?", s):
        ts = float(s)
        if ts > 1e11:                                     # milliseconds
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
```

### Step 6: Use it, and report instead of crashing

```python
for rec in records:
    email = first(rec, "email", "contact.email", "user.emails.0")
    amount = to_number(get_path(rec, "payout.amount"))
    paid_at = to_datetime(first(rec, "paid_at", "meta.paidAt", convert=lambda v: v))
    if amount is None:
        errors.append({"id": rec.get("id"), "error": "invalid_amount"})
        continue
    rows.append({"id": rec["id"], "email": email, "amount": amount, "paid_at": paid_at})
```

Pass `convert=lambda v: v` to `first` when you want the raw value (a number, say) rather than a cleaned string.

---

## Part 2: Redacting PII

### Step 7: Know what you're looking for

Common identifiers include emails, phone numbers, card numbers and US Social Security numbers. Each gets a regex and a label, so the redacted text still tells a reader *what* was removed: `[EMAIL]`, `[PHONE]`.

### Step 8: Order matters

Run the card pattern **before** the phone pattern. Otherwise the phone regex grabs ten digits from the middle of a card number and leaves the rest behind.

### Step 9: Cut false positives

A plain 13-digit run is often an order ID, not a card. Two guards help:

- **Cards must pass the Luhn checksum** that every real card number satisfies.
- **Phones must contain separators** (`555-123-4567`, `(555) 123 4567`). A bare run of ten digits is left alone.

### Step 10: Count what you redacted

Return per-type counts with the redacted text. That's how you report "redacted 3 emails in this export" in an audit log, without logging the emails themselves.

### The complete snippet

```python
import re

PII_PATTERNS = [                                          # order matters: cards before phones
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?!\d)")),
]


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def redact(text: str):
    """Returns (redacted_text, {"EMAIL": 1, ...}). Cards only count if they pass the Luhn check.
    Phones need separators ("555-123-4567", "(555) 123 4567", "+1 555.123.4567") so IDs aren't redacted."""
    counts = {}

    def replace(kind):
        def sub(m):
            if kind == "CARD" and not _luhn_ok(re.sub(r"\D", "", m.group())):
                return m.group()
            counts[kind] = counts.get(kind, 0) + 1
            return f"[{kind}]"
        return sub

    for kind, pattern in PII_PATTERNS:
        text = pattern.sub(replace(kind), text)
    return text, counts


def redact_obj(obj):
    """Redact every string inside nested dicts/lists. Returns a new object."""
    if isinstance(obj, str):
        return redact(obj)[0]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    return obj
```

### Step 11: Where to call it

```python
# Before an LLM call
clean_text, found = redact(ticket["body"])
category = ask_llm(system_prompt, "<input>" + json.dumps(clean_text) + "</input>", validate=...)

# Before writing an export
atomic_write_json(out_path, [redact_obj(r) for r in records])

# Before logging
log.info("ticket received: %s", redact(ticket["body"])[0])
```

> Regex redaction is a safety net, not a guarantee. Names and street addresses need a proper NER model. Keep raw PII out of logs in the first place, and redact at the boundaries where data leaves your system.

---

## Testing

```python
def test_normalizers():
    rec = {"email": "null", "contact": {"email": " Ada@X.com "}, "items": [{"id": 7}]}
    assert get_path(rec, "items.0.id") == 7
    assert first(rec, "email", "contact.email") == "Ada@X.com"
    assert [to_number(v) for v in ["12", " $1,234.50 ", True, "nan"]] == [12, 1234.5, None, None]
    assert to_datetime(1709546400000) == to_datetime("2024-03-04T10:00:00Z")


def test_redact():
    text, counts = redact("ada@x.com, (555) 123-4567, card 4111 1111 1111 1111, order 1234567890123")
    assert counts == {"EMAIL": 1, "PHONE": 1, "CARD": 1}
    assert "1234567890123" in text            # not a valid card, not a formatted phone
```

---

## Recap

1. **Walk paths safely** with one `get_path`, and **fall back** across fields with `first`.
2. **Define "missing" once.**
3. **Parse strictly:** reject booleans, NaN and junk, and return `None` so the caller can report it.
4. **Detect epoch milliseconds,** and always return UTC-aware datetimes.
5. **Redact PII at the boundaries** (LLM calls, exports, logs), with labels and counts. Order the patterns carefully and use checksums to avoid false positives.

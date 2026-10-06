TRUE_WORDS = {"true", "yes", "y", "1", "up", "ok"}


def clean_id(value):
    return (value or "").strip().lower()


def parse_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in TRUE_WORDS
    return bool(value)


def parse_ms(value, default=None):
    """'1200', ' 1200 ', '1.5s' -> milliseconds as int. Blank -> default."""
    text = (value or "").strip().lower()
    if not text:
        return default
    if text.endswith("ms"):
        return int(text[:-2])
    if text.endswith("s"):
        return int(round(float(text[:-1]) * 1000))
    return int(text)

from datetime import datetime

DEFAULT_LOCALE = "en-us"
TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_task(value):
    return clean(value).upper()


def norm_model(value):
    return clean(value).lower()


def norm_locale(value):
    return clean(value).lower() or DEFAULT_LOCALE


def parse_ts(value):
    text = clean(value)
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S")

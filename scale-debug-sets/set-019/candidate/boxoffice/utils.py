from datetime import datetime

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time: {value!r}")


def age_seconds(earlier, later):
    return (later - earlier).seconds

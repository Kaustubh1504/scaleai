class RowError(ValueError):
    """A row that cannot be ingested."""


class MissingField(RowError):
    """A required field is blank or absent."""


REQUIRED = ("email",)

DEFAULTS = {
    "name": "",
    "skills": [],
    "hourly_rate": None,
    "country": "UNKNOWN",
    "notes": [],
}

COUNTRY_ALIASES = {
    "USA": "US",
    "UNITED STATES": "US",
    "UK": "GB",
    "INDIA": "IN",
}


def norm_country(raw):
    code = str(raw or "").strip().upper()
    if not code:
        return "UNKNOWN"
    return COUNTRY_ALIASES.get(code, code)

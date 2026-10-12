# 41. Secrets and config from the environment

The labeling-export job has its API key pasted into the source and a timeout
of `"30"` (a string) passed straight to httpx. A bad deploy then failed three
times in a row, each time on the *next* missing variable. You're writing the
settings loader every service will share: read config from the environment,
validate it all up front, report **every** problem at once, and never leak the
key into logs.

## Input

Environment variables (strings):

| name          | required | rule                                                         | default |
|---------------|----------|--------------------------------------------------------------|---------|
| `API_KEY`     | yes      | non-blank                                                    |         |
| `BASE_URL`    | yes      | starts with `https://`; trailing `/`s stripped                |         |
| `TIMEOUT_S`   | no       | a finite float `> 0`                                          | `10.0`  |
| `MAX_RETRIES` | no       | an int `>= 0` (`"2.5"` is invalid)                            | `3`     |
| `LOG_LEVEL`   | no       | `DEBUG`, `INFO`, `WARNING` or `ERROR`, case-insensitive, stored upper-case | `"INFO"` |

Whitespace around every value is stripped first. A blank value (`""`, `"  "`)
counts as **missing**: an error for required variables, the default for optional ones.

## Setup

```python
Settings.from_env({"API_KEY": "sk_live_x", "BASE_URL": "https://api.scale.test"})  # tests pass plain dicts
load_settings(tmp_path / ".env", env={...})                                       # or a .env path + env
```

There is no `problem_api`; tests also use `monkeypatch` on `os.environ`. Your file
starts empty. An `if __name__ == "__main__":` block is what the Run button
executes: use it to see what a default dataclass `repr` would leak.

## Your task

Write in your file:

* `ConfigError(Exception)`: constructed with a `problems: list[str]` (one message per bad variable), stored as `.problems`; its `str()` should summarise them.
* `Settings`: frozen dataclass, fields `api_key: str, base_url: str, timeout_s: float = 10.0, max_retries: int = 3, log_level: str = "INFO"`.
* `Settings.from_env(env: Mapping[str, str] | None = None) -> Settings` (classmethod)
* `load_dotenv(path: str | Path) -> dict[str, str]`
* `load_settings(dotenv_path: str | Path | None = None, env: Mapping[str, str] | None = None) -> Settings`

Rules:

* `from_env(env)` validates every variable and, if anything is wrong, raises
  **one** `ConfigError` whose `.problems` has an entry for **each** bad
  variable, each message containing that variable's name.
* `from_env()` with no argument reads `os.environ` **at call time**.
* `repr(settings)` and `str(settings)` show the key as `***`, never the
  value. `ConfigError` messages never contain the `API_KEY` value either.
* `Settings` is immutable (assigning a field raises `FrozenInstanceError`).
* `load_dotenv(path)`: parse a `.env` file into a dict. One `KEY=VALUE` per
  line; blank lines and lines starting with `#` are skipped; an optional
  `export ` prefix is allowed; whitespace around key and value is stripped; a
  value wrapped in matching `"` or `'` has the quotes removed. Lines without
  `=` are skipped. A missing file raises `FileNotFoundError`.
* `load_settings(dotenv_path, env)`: merge the `.env` values (if a path is
  given **and** the file exists) under the real environment (`env`, or
  `os.environ` if `None`). **Real environment variables always win.**

## Example

```
from_env({"API_KEY": "sk_live_abc", "BASE_URL": "https://api.scale.test/", "LOG_LEVEL": "debug"})
→ Settings(api_key='***', base_url='https://api.scale.test', timeout_s=10.0, max_retries=3, log_level='DEBUG')

from_env({"BASE_URL": "http://x", "TIMEOUT_S": "0"})
→ ConfigError: 3 config problem(s): API_KEY is required; BASE_URL must start with https:// ...; TIMEOUT_S must be ... > 0
```

## Constraints

* Don't print or log the key. Don't read `os.environ` at import time.

<details><summary>Hint 1</summary>

Collect messages in a `problems: list[str]` while parsing each variable, and
raise once at the end. A small `_get(name)` that strips and turns blank into
`None` keeps it tidy.
</details>

<details><summary>Hint 2</summary>

`field(repr=False)` hides a field entirely; to show `***` write `__repr__`
yourself (a dataclass uses it for `str` too). `env = os.environ if env is None else env`
inside the function, never as a default argument value.
</details>

## Follow-up (talk it through)

* Where should secrets live in production (env vars, a secrets manager, mounted files)? How do you rotate one?
* Why fail at startup on bad config instead of on first use?

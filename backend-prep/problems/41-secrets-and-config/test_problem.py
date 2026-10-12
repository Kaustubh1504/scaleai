import dataclasses

import pytest

GOOD = {"API_KEY": "sk_live_SECRET123", "BASE_URL": "https://api.scale.test"}
NAMES = ("API_KEY", "BASE_URL", "TIMEOUT_S", "MAX_RETRIES", "LOG_LEVEL")


def clean_environ(monkeypatch):
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)


def test_required_and_defaults(sol):
    """from_env reads required values and applies defaults"""
    s = sol.Settings.from_env(dict(GOOD))
    assert (s.api_key, s.base_url) == ("sk_live_SECRET123", "https://api.scale.test")
    assert s.timeout_s == 10.0 and isinstance(s.timeout_s, float)
    assert s.max_retries == 3 and s.log_level == "INFO"


def test_parses_and_normalises(sol):
    """from_env strips whitespace and trailing slashes, parses numbers, upper-cases LOG_LEVEL"""
    env = {"API_KEY": "  sk_x  ", "BASE_URL": " https://api.scale.test/v2// ", "TIMEOUT_S": "2.5",
           "MAX_RETRIES": "0", "LOG_LEVEL": "debug"}
    s = sol.Settings.from_env(env)
    assert s.api_key == "sk_x"
    assert s.base_url == "https://api.scale.test/v2", "strip whitespace and trailing slashes"
    assert s.timeout_s == 2.5 and s.max_retries == 0 and s.log_level == "DEBUG"


def test_blank_optional_uses_default(sol):
    """A blank optional variable falls back to its default"""
    s = sol.Settings.from_env({**GOOD, "TIMEOUT_S": "  ", "LOG_LEVEL": ""})
    assert s.timeout_s == 10.0 and s.log_level == "INFO"


def test_all_problems_at_once(sol):
    """Every bad variable is reported in a single ConfigError"""
    env = {"API_KEY": "   ", "BASE_URL": "http://api.scale.test", "TIMEOUT_S": "fast",
           "MAX_RETRIES": "2.5", "LOG_LEVEL": "TRACE"}
    with pytest.raises(sol.ConfigError) as exc:
        sol.Settings.from_env(env)
    problems = exc.value.problems
    for name in ("API_KEY", "BASE_URL", "TIMEOUT_S", "MAX_RETRIES", "LOG_LEVEL"):
        assert any(name in p for p in problems), f"no problem mentions {name}: {problems}"
    assert len(problems) == 5, f"expected exactly one problem per bad variable, got {problems}"


def test_numeric_ranges(sol):
    """TIMEOUT_S must be finite and > 0; MAX_RETRIES must be >= 0"""
    for bad in ({"TIMEOUT_S": "0"}, {"TIMEOUT_S": "-1"}, {"TIMEOUT_S": "nan"}, {"TIMEOUT_S": "inf"},
                {"MAX_RETRIES": "-1"}):
        with pytest.raises(sol.ConfigError) as exc:
            sol.Settings.from_env({**GOOD, **bad})
        (name,) = bad
        assert any(name in p for p in exc.value.problems), f"{bad} should be reported"


def test_secret_never_shown(sol):
    """repr/str show *** for the key, and error messages never contain it"""
    s = sol.Settings.from_env(dict(GOOD))
    for text in (repr(s), str(s), f"{s}"):
        assert "sk_live_SECRET123" not in text, f"API key leaked: {text}"
        assert "***" in text
        assert "https://api.scale.test" in text, "non-secret fields should still be visible"
    with pytest.raises(sol.ConfigError) as exc:
        sol.Settings.from_env({**GOOD, "TIMEOUT_S": "x", "LOG_LEVEL": "nope"})
    assert "sk_live_SECRET123" not in str(exc.value) + repr(exc.value.problems)


def test_frozen(sol):
    """Settings is immutable"""
    s = sol.Settings.from_env(dict(GOOD))
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.api_key = "other"


def test_reads_os_environ_at_call_time(sol, monkeypatch):
    """from_env() with no argument reads os.environ when called"""
    clean_environ(monkeypatch)
    monkeypatch.setenv("API_KEY", "sk_from_env")
    monkeypatch.setenv("BASE_URL", "https://env.scale.test/")
    monkeypatch.setenv("MAX_RETRIES", "7")
    s = sol.Settings.from_env()
    assert (s.api_key, s.base_url, s.max_retries) == ("sk_from_env", "https://env.scale.test", 7)
    monkeypatch.setenv("MAX_RETRIES", "1")
    assert sol.Settings.from_env().max_retries == 1, "must not cache os.environ from import time"


def test_load_dotenv(sol, tmp_path):
    """load_dotenv handles comments, blanks, export, quotes and whitespace"""
    path = tmp_path / ".env"
    path.write_text(
        "# local dev settings\n"
        "\n"
        "API_KEY=sk_dotenv\n"
        "export BASE_URL = 'https://dotenv.scale.test'\n"
        'LOG_LEVEL="warning"\n'
        "TIMEOUT_S= 4 \n"
        "not a setting\n"
        'EMPTY=""\n'
    )
    assert sol.load_dotenv(path) == {"API_KEY": "sk_dotenv", "BASE_URL": "https://dotenv.scale.test",
                                     "LOG_LEVEL": "warning", "TIMEOUT_S": "4", "EMPTY": ""}
    with pytest.raises(FileNotFoundError):
        sol.load_dotenv(tmp_path / "missing.env")


def test_real_env_wins(sol, tmp_path, monkeypatch):
    """load_settings: real environment variables override .env; a missing .env file is fine"""
    path = tmp_path / ".env"
    path.write_text("API_KEY=sk_dotenv\nBASE_URL=https://dotenv.scale.test\nMAX_RETRIES=9\n")
    s = sol.load_settings(path, env={"API_KEY": "sk_real", "LOG_LEVEL": "error"})
    assert s.api_key == "sk_real", ".env must never override the real environment"
    assert s.base_url == "https://dotenv.scale.test" and s.max_retries == 9 and s.log_level == "ERROR"

    clean_environ(monkeypatch)
    monkeypatch.setenv("API_KEY", "sk_os")
    monkeypatch.setenv("BASE_URL", "https://os.scale.test")
    s = sol.load_settings(tmp_path / "nope.env")
    assert (s.api_key, s.base_url) == ("sk_os", "https://os.scale.test")

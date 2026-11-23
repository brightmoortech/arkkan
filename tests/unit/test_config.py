"""Stage 1 configuration tests; no database connection is made."""

import pytest

from arkkan._config import _connection_settings


def test_s1_002_required_settings() -> None:
    settings = {"PGDATABASE": "test_db", "PGUSER": "test_user"}
    assert _connection_settings(settings) == settings


@pytest.mark.parametrize("variable", ["PGDATABASE", "PGUSER"])
@pytest.mark.parametrize("value", [None, "", " \t\n"])
def test_s1_003_required_validation(variable: str, value: str | None) -> None:
    settings = {"PGDATABASE": "test_db", "PGUSER": "test_user"}
    if value is None:
        del settings[variable]
    else:
        settings[variable] = value
    with pytest.raises(ValueError, match=rf"^{variable} is required"):
        _connection_settings(settings)


def test_s1_004_optional_settings() -> None:
    settings = {
        "PGDATABASE": "test_db",
        "PGUSER": "test_user",
        "PGHOST": "/tmp/socket",
        "PGPORT": "5433",
        "PGPASSFILE": "/example/password-file",
    }
    assert _connection_settings(settings) == settings


def test_s1_005_preserve_values_and_exclude_credentials() -> None:
    settings = {
        "PGDATABASE": " Exact Database ",
        "PGUSER": "Exact User",
        "PGPASSWORD": "synthetic-secret",
        "UNRELATED": "ignored",
    }
    assert _connection_settings(settings) == {
        "PGDATABASE": " Exact Database ",
        "PGUSER": "Exact User",
    }


def test_s1_006_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PGDATABASE", "test_db")
    monkeypatch.setenv("PGUSER", "test_user")
    for variable in ("PGHOST", "PGPORT", "PGPASSFILE"):
        monkeypatch.delenv(variable, raising=False)
    assert _connection_settings() == {
        "PGDATABASE": "test_db",
        "PGUSER": "test_user",
    }

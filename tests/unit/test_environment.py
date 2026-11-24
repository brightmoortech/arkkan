"""Environment contract tests; no Docker or database changes are made."""

import os
from pathlib import Path

import pytest

from arkkan._environment import (
    _ALLOWED,
    _REQUIRED,
    _read_environment,
    _validate_environment,
)


@pytest.fixture
def environment(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    for name in ("provisioning", "pgpass"):
        file = tmp_path / name
        file.write_text("synthetic-test-data", encoding="utf-8")
        file.chmod(0o600)
    return checkout, {
        "ARKKAN_ENVIRONMENT": "staging",
        "COMPOSE_PROJECT_NAME": "example_stage",
        "POSTGRES_CONTAINER_NAME": "example-db-test",
        "PGHOST": "localhost",
        "PGPORT": "5434",
        "PGDATABASE": "example_test",
        "PGUSER": "example_superuser",
        "PGPASSFILE": str(tmp_path / "pgpass"),
        "POSTGRES_DATA_DIR": str(tmp_path / "data" / "postgres"),
        "POSTGRES_PASSWORD_FILE": str(tmp_path / "provisioning"),
    }


def test_s2_001_literal_configuration(tmp_path: Path) -> None:
    file = tmp_path / ".env"
    file.write_text(
        "# Comment\n\nPGHOST=localhost\nPGDATABASE=db name\n",
        encoding="utf-8",
    )
    assert _read_environment(file) == {
        "PGHOST": "localhost", "PGDATABASE": "db name",
    }


@pytest.mark.parametrize("content", [
    "PGHOST=localhost\nPGHOST=other\n",
    "PGPASSWORD=synthetic-secret\n",
    "PGHOST=$(id)\n",
    "export PGHOST=localhost\n",
    "PGHOST='localhost'\n",
    "PGHOST= localhost\n",
    "PGHOST=localhost # comment\n",
])
def test_s2_002_reject_invalid_configuration(
    tmp_path: Path,
    content: str
) -> None:
    file = tmp_path / ".env"
    file.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid or duplicate") as error:
        _read_environment(file)
    assert "synthetic-secret" not in str(error.value)


def test_s2_003_valid_contract_does_not_write(
    environment: tuple[Path, dict[str, str]]
) -> None:
    root, settings = environment
    before = {
        name: Path(settings[name]).read_bytes()
        for name in ("PGPASSFILE", "POSTGRES_PASSWORD_FILE")
    }
    assert _validate_environment(settings, root) == settings
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()
    assert before == {
        name: Path(settings[name]).read_bytes() for name in before
    }


@pytest.mark.parametrize("value", [None, ""])
@pytest.mark.parametrize("key", [
    "ARKKAN_ENVIRONMENT", "COMPOSE_PROJECT_NAME", "POSTGRES_CONTAINER_NAME",
    "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "POSTGRES_DATA_DIR",
    "POSTGRES_PASSWORD_FILE",
])
def test_s2_004_missing_required_setting(
    environment: tuple[Path, dict[str, str]], key: str, value: str | None
) -> None:
    root, settings = environment
    if value is None:
        del settings[key]
    else:
        settings[key] = value
    with pytest.raises(ValueError, match=key):
        _validate_environment(settings, root)


@pytest.mark.parametrize(("key", "value"), [
    ("ARKKAN_ENVIRONMENT", "test"), ("COMPOSE_PROJECT_NAME", "Bad Name"),
    ("POSTGRES_CONTAINER_NAME", "bad/name"), ("PGPORT", "0"),
    ("PGPORT", "65536"), ("PGPORT", "-1"), ("PGPORT", "port"),
    ("PGHOST", "example.com"), ("PGUSER", "arkkan_user"),
    ("PGUSER", "arkkan_admin"), ("PGDATABASE", "template1"),
])
def test_s2_005_invalid_value(
    environment: tuple[Path, dict[str, str]],
    key: str,
    value: str
) -> None:
    root, settings = environment
    settings[key] = value
    with pytest.raises(ValueError, match=key):
        _validate_environment(settings, root)


@pytest.mark.parametrize("key", ["POSTGRES_PASSWORD_FILE", "PGPASSFILE"])
def test_s2_006_password_file_validation(
    environment: tuple[Path, dict[str, str]],
    key: str
) -> None:
    root, settings = environment
    file = Path(settings[key])
    file.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        _validate_environment(settings, root)
    file.unlink()
    with pytest.raises(ValueError, match=key):
        _validate_environment(settings, root)


@pytest.mark.parametrize("alias", [False, True])
def test_s2_007_password_files_separate(
    environment: tuple[Path, dict[str, str]], alias: bool
) -> None:
    root, settings = environment
    if alias:
        passfile = Path(settings["PGPASSFILE"])
        passfile.unlink()
        os.link(settings["POSTGRES_PASSWORD_FILE"], passfile)
    else:
        settings["PGPASSFILE"] = settings["POSTGRES_PASSWORD_FILE"]
    with pytest.raises(ValueError, match="separate"):
        _validate_environment(settings, root)


@pytest.mark.parametrize(
    "location", ["inside", "ancestor", "file", "other_checkout"]
)
def test_s2_008_storage_location(
    environment: tuple[Path, dict[str, str]],
    location: str
) -> None:
    root, settings = environment
    other_checkout = root.parent / "other_checkout"
    (other_checkout / ".git").mkdir(parents=True)
    candidates = {
        "inside": root / "mnt",
        "ancestor": root.parent,
        "file": Path(settings["PGPASSFILE"]),
        "other_checkout": other_checkout / "mnt",
    }
    settings["POSTGRES_DATA_DIR"] = str(candidates[location])
    with pytest.raises(ValueError, match="POSTGRES_DATA_DIR"):
        _validate_environment(settings, root)


def test_s2_009_default_pgpass(
    environment: tuple[Path, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch
) -> None:
    root, settings = environment
    home = root.parent
    monkeypatch.setenv("HOME", str(home))
    passfile = home / ".pgpass"
    passfile.write_text("synthetic-test-data", encoding="utf-8")
    passfile.chmod(0o600)
    del settings["PGPASSFILE"]
    assert _validate_environment(settings, root)["PGPASSFILE"] == str(passfile)


def test_s2_010_driver_import() -> None:
    import psycopg
    from psycopg import pq

    assert psycopg.__version__ == "3.3.9"
    assert pq.__impl__ == "binary"


def test_s2_011_example_contract() -> None:
    root = Path(__file__).resolve().parents[2]

    settings = _read_environment(root / ".env.example")
    assert set(settings) == _ALLOWED
    assert set(_REQUIRED) <= set(settings)
    assert all(not value for key, value in settings.items() if key != "PGHOST")

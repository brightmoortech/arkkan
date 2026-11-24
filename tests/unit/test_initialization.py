"""Exercise initialization sequencing and the command contract without a database."""

import json
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from arkkan._db_migrations import _migration_list
from arkkan._migration_workflow import _Migration, _run_migrations
from arkkan._initialization_connection import _initialization_connection
from scripts.init_db import _settings

_ROOT = Path(__file__).resolve().parents[2]


class _Connection:
    """Record transaction boundaries and simulate rollback of step changes."""

    def __init__(self) -> None:
        self.autocommit = True
        self.info = SimpleNamespace(transaction_status=0)
        self.closed = False
        self.broken = False
        self.objects: set[str] = set()
        self.events: list[str] = []
        self.read_only = False
        self.lock_available = True

    @contextmanager
    def transaction(self) -> Iterator[None]:
        snapshot = self.objects.copy()
        assert self.info.transaction_status == 0
        self.info.transaction_status = 2
        self.read_only = False
        self.events.append("begin")
        try:
            yield
        except BaseException:
            self.objects = snapshot
            self.events.append("rollback")
            raise
        else:
            self.events.append("commit")
        finally:
            self.info.transaction_status = 0
            self.read_only = False

    def execute(self, statement: str, params: tuple[Any, ...] = ()) -> Any:
        self.events.append(statement)
        if statement == "SET TRANSACTION READ ONLY":
            self.read_only = True
        if "pg_try_advisory_lock" in statement:
            assert params == (42,)
            return SimpleNamespace(fetchone=lambda: (self.lock_available,))
        return SimpleNamespace(fetchone=lambda: (True,))


def _step(name: str, *, conflict: bool = False, fail: bool = False) -> _Migration:
    def _check(connection: _Connection) -> bool:
        assert connection.info.transaction_status == 2
        connection.events.append(f"check:{name}")
        if conflict:
            raise ValueError("conflicting object")
        return name in connection.objects

    def _apply(connection: _Connection) -> None:
        assert connection.info.transaction_status == 2 and not connection.read_only
        connection.events.append(f"apply:{name}")
        connection.objects.add(name)
        if fail:
            raise ValueError("injected step failure")

    return _Migration(name, _check, _apply)


def test_s2_051_dry_run_read_only() -> None:
    connection = _Connection()
    connection.objects.add("existing")
    output: list[str] = []
    _run_migrations(connection, [_step("existing"), _step("missing")],
                    apply=False, lock_key=42, report=output.append)
    assert connection.objects == {"existing"}
    assert connection.events == [
        "begin", "SET TRANSACTION READ ONLY", "SET LOCAL search_path = pg_catalog",
        "check:existing", "check:missing", "commit",
    ]
    assert output == ["[UNCHANGED] existing", "[PENDING] missing",
                      "[OK] Dry run complete. No database changes made."]


@pytest.mark.parametrize("apply", [False, True])
def test_s2_052_late_conflict_prevents_writes(apply: bool) -> None:
    connection = _Connection()
    with pytest.raises(ValueError, match="late: conflicting object"):
        _run_migrations(connection, [_step("early"), _step("late", conflict=True)],
                        apply=apply, lock_key=42)
    assert not connection.objects
    assert "apply:early" not in connection.events
    if apply:
        assert connection.events[-1].startswith("SELECT pg_catalog.pg_advisory_unlock")


def test_s2_053_step_failure_rolls_back_and_stops() -> None:
    connection = _Connection()
    output: list[str] = []
    with pytest.raises(ValueError, match="injected step failure"):
        _run_migrations(connection, [_step("first"), _step("failed", fail=True), _step("later")],
                        apply=True, lock_key=42, report=output.append)
    assert connection.objects == {"first"}
    assert "rollback" in connection.events
    assert "apply:later" not in connection.events
    assert any("1 earlier applied step(s) confirmed committed" in line for line in output)


def test_s2_054_apply_rerun_reuses_existing_objects() -> None:
    connection = _Connection()
    connection.objects.add("first")
    steps = [_step("first"), _step("second")]
    _run_migrations(connection, steps, apply=True, lock_key=42)
    assert connection.objects == {"first", "second"}
    assert "apply:first" not in connection.events
    assert connection.events.count("apply:second") == 1
    _run_migrations(connection, steps, apply=True, lock_key=42)
    assert connection.events.count("apply:second") == 1


@pytest.mark.parametrize("invalid", ["duplicate", "empty", "busy", "nonidle", "no_autocommit"])
def test_s2_055_workflow_guards(invalid: str) -> None:
    connection = _Connection()
    steps = [_step("step")]
    if invalid == "duplicate":
        steps *= 2
    elif invalid == "empty":
        steps = []
    elif invalid == "busy":
        connection.lock_available = False
    elif invalid == "nonidle":
        connection.info.transaction_status = 2
    else:
        connection.autocommit = False
    with pytest.raises(ValueError):
        _run_migrations(connection, steps, apply=True, lock_key=42)
    assert not connection.objects
    assert "begin" not in connection.events


@pytest.mark.parametrize("args,code", [
    (["--help"], 0), (["--check", "--apply"], 2), (["--unknown"], 2),
    (["--app"], 2), (["unexpected"], 2),
])
def test_s2_056_command_arguments_no_connection(args: list[str], code: int) -> None:
    result = subprocess.run([sys.executable, "scripts/init_db.py", *args], cwd=_ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == code, result.stderr
    if code == 0:
        assert "Dry run (default)" in result.stdout
    else:
        assert "usage:" in result.stderr
    assert "[APPLIED]" not in result.stdout


@pytest.fixture
def _configuration(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    root = tmp_path / "project"
    root.mkdir()
    passfile = tmp_path / "pgpass"
    passfile.write_text("localhost:5442:testdb:operator:synthetic-test-data\n")
    passfile.chmod(0o600)
    settings = {"PGHOST": "localhost", "PGPORT": "5442", "PGDATABASE": "testdb",
                "PGUSER": "operator", "PGPASSFILE": str(passfile)}
    return root, passfile, settings


def test_s2_057_connection_settings(_configuration: tuple[Path, Path, dict[str, str]]) -> None:
    root, passfile, settings = _configuration
    assert _settings(root, settings) == (settings, passfile, None)
    env_file = root / ".env"
    env_file.write_text("ARKKAN_ENVIRONMENT=staging\n" + "\n".join(
        f"{key}={value}" for key, value in settings.items()) + "\n")
    assert _settings(root, {}) == (settings, passfile, "staging")
    before = passfile.read_bytes()
    assert _settings(root, {"PGPORT": "5442"}) == (settings, passfile, "staging")
    assert passfile.read_bytes() == before
    assert not (root / "postgres").exists()


@pytest.mark.parametrize("problem", ["missing_db", "missing_user", "api_role", "maintenance_db",
                                     "extra_pg", "unsafe_passfile", "missing_passfile",
                                     "conflict", "invalid_identity"])
def test_s2_058_reject_unsafe_configuration(
    _configuration: tuple[Path, Path, dict[str, str]], problem: str,
) -> None:
    root, passfile, settings = _configuration
    if problem == "missing_db":
        del settings["PGDATABASE"]
    elif problem == "missing_user":
        del settings["PGUSER"]
    elif problem == "api_role":
        settings["PGUSER"] = "arkkan_user"
    elif problem == "maintenance_db":
        settings["PGDATABASE"] = "postgres"
    elif problem == "extra_pg":
        settings["PGPASSWORD"] = "synthetic-test-data"
    elif problem == "unsafe_passfile":
        passfile.chmod(0o644)
    elif problem == "missing_passfile":
        passfile.unlink()
    else:
        identity = "unknown" if problem == "invalid_identity" else "staging"
        (root / ".env").write_text(f"ARKKAN_ENVIRONMENT={identity}\n" + "\n".join(
            f"{key}={value}" for key, value in settings.items()) + "\n")
        settings = {"PGPORT": "9999"} if problem == "conflict" else {}
    with pytest.raises(ValueError) as error:
        _settings(root, settings)
    assert "synthetic-test-data" not in str(error.value)


def test_s2_059_migration_manifest_and_seed_mapping() -> None:
    migrations = _migration_list(_ROOT)
    assert len(migrations) == 12
    assert [migration.name[:3] for migration in migrations] == [f"{n:03}" for n in range(1, 13)]
    folder = _ROOT / "sql" / "migrations"
    assert {f"{migration.name}.sql" for migration in migrations} == {
        path.name for path in folder.glob("*.sql")
    }
    seeds = json.loads((folder / "012_resource_types.json").read_text())
    functional = (_ROOT / "arkkan.wiki" / "FUNCTIONAL_REQ.md").read_text()
    expected = {}
    for line in functional.splitlines():
        parts = line.strip("|").split("|")
        if len(parts) == 2 and parts[0].strip().lower() in seeds:
            expected[parts[0].strip().lower()] = parts[1].strip()
    assert len(expected) == 7 and seeds == expected


@pytest.mark.parametrize("problem", [None, "database", "role", "version", "privilege", "recovery"])
def test_s2_068_connection_prerequisites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, problem: str | None,
) -> None:
    settings = {"PGHOST": "localhost", "PGPORT": "5442",
                "PGDATABASE": "target", "PGUSER": "operator"}
    row: list[Any] = ["target", "operator", 180007, True, False]
    changes = {"database": (0, "other"), "role": (1, "other"),
               "version": (2, 170000), "privilege": (3, False),
               "recovery": (4, True)}
    if problem is not None:
        index, value = changes[problem]
        row[index] = value
    statements: list[str] = []
    options: dict[str, Any] = {}

    class _FakeConnection:
        @contextmanager
        def transaction(self) -> Iterator[None]:
            yield

        def execute(self, statement: str) -> Any:
            statements.append(statement)
            return SimpleNamespace(fetchone=lambda: tuple(row))

    @contextmanager
    def _connect(**kwargs: Any) -> Iterator[_FakeConnection]:
        options.update(kwargs)
        yield _FakeConnection()

    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(connect=_connect))
    passfile = tmp_path / "pgpass"
    if problem is None:
        with _initialization_connection(settings, required_major=18,
                                        password_file=passfile, local_scram=True):
            pass
    else:
        with pytest.raises(ValueError):
            with _initialization_connection(settings, required_major=18,
                                            password_file=passfile, local_scram=True):
                pytest.fail("Invalid connection must not be yielded.")
    assert statements[:2] == ["SET TRANSACTION READ ONLY",
                              "SET LOCAL search_path = pg_catalog"]
    assert options["passfile"] == str(passfile)
    assert options["require_auth"] == "scram-sha-256"
    assert options["autocommit"] is True and options["hostaddr"] == "127.0.0.1"
    assert "password" not in options

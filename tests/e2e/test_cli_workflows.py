"""Real installed CLI workflows, restricted to the verified staging target."""

from collections.abc import Callable, Iterator
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import subprocess
import sys
from typing import Any

from psycopg import sql
import pytest

from arkkan._provisioning import _load_settings
from arkkan._test_safety import _staging_connection
from integration.test_db_initialization import _reset_application, _run

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli(tmp_path: Path) -> Iterator[Callable[..., subprocess.CompletedProcess[bytes]]]:
    _reset_application()
    password_file = tmp_path / "pgpass"
    try:
        _run(apply=True)
        settings = _load_settings(_ROOT)
        entries = []
        with _staging_connection(_ROOT) as connection:
            for role in ("arkkan_admin", "arkkan_user"):
                password = token_urlsafe(32)
                connection.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)))
                fields = [settings["PGHOST"], settings["PGPORT"], settings["PGDATABASE"],
                          role, password]
                entries.append(":".join(value.replace("\\", "\\\\").replace(":", "\\:")
                                        for value in fields))
        with open(password_file, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            stream.write("\n".join(entries) + "\n")
        original = password_file.read_bytes()
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("PG")}
        environment.update({key: settings[key] for key in ("PGHOST", "PGPORT", "PGDATABASE")})
        # Subprocesses use real public API/driver code; no monkeypatch enters them.
        def invoke(
            *arguments: str, role: str = "arkkan_admin", content: bytes = b"",
            missing_password: bool = False,
        ) -> subprocess.CompletedProcess[bytes]:
            assert role in {"arkkan_admin", "arkkan_user"}
            child_environment = environment | {
                "PGUSER": role,
                "PGPASSFILE": str(tmp_path / "missing" if missing_password else password_file),
            }
            with _staging_connection(_ROOT):
                result = subprocess.run(
                    [str(Path(sys.executable).parent / "arkkan"), *arguments],
                    cwd=tmp_path, env=child_environment, input=content,
                    capture_output=True, check=False, timeout=30,
                )
            assert password_file.read_bytes() == original
            assert password_file.stat().st_mode & 0o777 == 0o600
            assert b"Traceback" not in result.stderr
            return result

        yield invoke
    finally:
        password_file.unlink(missing_ok=True)
        _reset_application()


def _json(result: subprocess.CompletedProcess[bytes], operation: str, *, success: bool = True) -> Any:
    assert result.returncode == (0 if success else 1), result.stderr
    assert result.stderr == b""
    response = json.loads(result.stdout)
    assert response["operation_name"] == operation
    assert response["message_type"] == "response"
    assert response["result"] == ("success" if success else "error")
    key = "data" if success else "reason"
    assert set(response) == {"operation_name", "message_type", "result", key}
    if not success:
        assert isinstance(response[key], str) and response[key].strip()
    return response[key]


def test_s5_025_creation_reads_and_metadata(cli: Callable, tmp_path: Path) -> None:
    slug = " r 雪 '; -- "
    content = "\ufeff雪 العربية\r\n  \t\n".encode("utf-8")
    source = tmp_path / "prompt.txt"
    source.write_bytes(content)
    _json(cli("type", "add", "custom", "-d", "original", "-j"), "add_resource_type")
    _json(cli("type", "update", "custom", "--clear-description", "-j"), "update_resource_type")
    _json(cli("resource", "add", slug, "v1", "-t", "custom", "-f", str(source),
              "-n", "Original", "-d", "Original", "-s", "enabled_default", "-j"), "add_resource")
    _json(cli("resource", "add", slug, "v2", "-f", "-", "-s", "enabled", "-j",
              content=b"second\r\n"), "add_resource")
    _json(cli("resource", "add", slug, "empty", "-s", "enabled", "-j"), "add_resource")
    _json(cli("resource", "update", slug, "-n", "", "-d", "",
              "-v", "v2", "-i", "revised", "-j"), "update_resource")
    info = _json(cli("resource", "info", slug, "-j"), "get_resource_info")
    assert info["name"] == "" and info["description"] == ""
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("SELECT version_info FROM arkkan.resource_versions WHERE version='v2'").fetchone() == ("revised",)
    _json(cli("resource", "update", slug, "--clear-name", "--clear-description",
              "-v", "v2", "--clear-info", "-j"), "update_resource")
    for role in ("arkkan_admin", "arkkan_user"):
        for options, expected in [([], content), (["-v", "v2"], b"second\r\n"),
                                  (["-v", "empty"], b""),
                                  (["-v", "missing", "-m", "version_priority"], content),
                                  (["-v", "v2", "-m", "default_priority"], content),
                                  (["-v", "v2", "-m", "strict"], b"second\r\n")]:
            result = cli("resource", "get", slug, *options, role=role)
            assert (result.returncode, result.stdout, result.stderr) == (0, expected, b"")
        data = _json(cli("resource", "get", slug, "-j", role=role), "get_resource_content")
        assert data["content"].encode("utf-8") == content
        info = _json(cli("resource", "info", slug, "-j", role=role), "get_resource_info")
        assert info["name"] is None and info["description"] is None
        assert len(info["versions"]) == 3 and "content" not in info
        assert _json(cli("resource", "default", slug, "-j", role=role),
                     "get_resource_version_default")["version"] == "v1"
        assert len(_json(cli("resource", "list", "-t", "custom", "-j", role=role),
                         "list_resources_matching_type")) == 1
    assert source.read_bytes() == content
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("SELECT description FROM arkkan.resource_types WHERE slug='custom'").fetchone() == (None,)
        assert connection.execute("SELECT version_info FROM arkkan.resource_versions WHERE version='v2'").fetchone() == (None,)


def test_s5_026_lifecycle_and_deletion(cli: Callable) -> None:
    _json(cli("type", "add", "custom", "-j"), "add_resource_type")
    _json(cli("resource", "add", "r", "v1", "-t", "custom", "-s", "enabled_default", "-j"), "add_resource")
    _json(cli("resource", "add", "r", "v2", "-j"), "add_resource")
    before = _json(cli("resource", "info", "r", "-j"), "get_resource_info")
    for arguments, operation in [
        (("state", "r", "-v", "v1", "-s", "disabled"), "set_resource_state"),
        (("state", "r", "-v", "v1", "-s", "obsolete", "-F"), "set_resource_state"),
        (("state-all", "r", "-s", "obsolete"), "set_resource_state_all"),
        (("state-matching", "r", "-g", "enabled_default", "-s", "disabled"), "set_resource_state_all_with_guard"),
        (("delete-version", "r", "-v", "v1"), "delete_resource_version"),
        (("delete", "r"), "delete_resource"),
    ]:
        _json(cli("resource", *arguments, "-j"), operation, success=False)
    _json(cli("type", "delete", "custom", "-j"), "delete_resource_type", success=False)
    _json(cli("type", "delete", "task", "-j"), "delete_resource_type", success=False)
    assert _json(cli("resource", "info", "r", "-j"), "get_resource_info") == before
    _json(cli("resource", "state", "r", "-v", "v1", "-s", "disabled", "-F", "-j"), "set_resource_state")
    assert _json(cli("resource", "state-all", "r", "-s", "obsolete", "-j"), "set_resource_state_all")["changed_count"] == 2
    _json(cli("resource", "delete-version", "r", "-v", "v1", "-j"), "delete_resource_version")
    for count in (1, 0):
        assert _json(cli("resource", "delete-obsolete", "r", "-j"), "delete_resource_version_all")["deleted_count"] == count
    assert _json(cli("resource", "info", "r", "-j"), "get_resource_info")["versions"] == []
    _json(cli("resource", "add", "r", "v3", "-j"), "add_resource")
    assert _json(cli("resource", "state-matching", "r", "-g", "disabled", "-s", "obsolete", "-j"), "set_resource_state_all_with_guard")["changed_count"] == 1
    for count in (1, 0):
        assert _json(cli("resource", "cleanup", "-j"), "clean_up")["deleted_count"] == count
    assert _json(cli("resource", "delete", "r", "-j"), "delete_resource")["deleted_version_count"] == 0
    result = cli("type", "delete", "custom")
    assert (result.returncode, result.stdout, result.stderr) == (0, b"Deleted type: custom\n", b"")


def test_s5_027_reader_denial_and_authentication(cli: Callable) -> None:
    commands = [
        (("type", "add", "custom"), "add_resource_type"),
        (("type", "update", "task", "-d", "changed"), "update_resource_type"),
        (("type", "delete", "task"), "delete_resource_type"),
        (("resource", "add", "r", "v", "-t", "task"), "add_resource"),
        (("resource", "update", "r", "-n", "changed"), "update_resource"),
        (("resource", "delete-version", "r", "-v", "v"), "delete_resource_version"),
        (("resource", "delete-obsolete", "r"), "delete_resource_version_all"),
        (("resource", "cleanup"), "clean_up"),
        (("resource", "delete", "r"), "delete_resource"),
        (("resource", "state", "r", "-v", "v", "-s", "disabled", "-F"), "set_resource_state"),
        (("resource", "state-all", "r", "-s", "disabled"), "set_resource_state_all"),
        (("resource", "state-matching", "r", "-g", "enabled", "-s", "disabled"), "set_resource_state_all_with_guard"),
    ]
    for arguments, operation in commands:
        reason = _json(cli(*arguments, "-j", role="arkkan_user"), operation, success=False)
        assert reason.startswith("Access denied.")
    result = cli("type", "add", "custom", role="arkkan_user")
    assert result.returncode == 1 and result.stdout == b""
    assert result.stderr.startswith(b"arkkan: Access denied.")
    reason = _json(cli("resource", "info", "r", "-j", role="arkkan_user", missing_password=True),
                   "get_resource_info", success=False)
    assert reason == "Database connection or operation failed. Check connection settings, credentials and server availability."
    assert _json(cli("resource", "info", "r", "-j", role="arkkan_user"),
                 "get_resource_info", success=False) == "Resource does not exist."
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("SELECT count(*) FROM arkkan.resource_definitions").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM arkkan.resource_types").fetchone() == (7,)


def test_s5_028_local_failures_preserve_database(cli: Callable, tmp_path: Path) -> None:
    source = tmp_path / "invalid.txt"
    source.write_bytes(b"private-content\xff")
    for arguments, content in [
        (("resource", "add", "r", "v", "-t", "task", "-f", str(source), "-j"), b""),
        (("resource", "add", "r", "v", "-t", "task", "-f", "-", "-j"), b"private-content\xff"),
        (("resource", "state-all", "r", "-s", "disabled", "-F"), b""),
    ]:
        result = cli(*arguments, content=content)
        assert result.returncode == 2 and result.stdout == b""
        assert b"error:" in result.stderr and b"private-content" not in result.stderr
    assert source.read_bytes() == b"private-content\xff"
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("SELECT count(*) FROM arkkan.resource_definitions").fetchone() == (0,)


def test_s5_029_database_failure_rolls_back(cli: Callable) -> None:
    with _staging_connection(_ROOT) as connection, connection.transaction():
        connection.execute("""CREATE FUNCTION public.cli_test_failure() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'private diagnostic'; END $$""")
        connection.execute("""CREATE TRIGGER cli_test_failure BEFORE INSERT ON
            arkkan.resource_versions FOR EACH ROW EXECUTE FUNCTION public.cli_test_failure()""")
    try:
        reason = _json(cli("resource", "add", "rollback", "v", "-t", "task", "-j"),
                       "add_resource", success=False)
        assert "private diagnostic" not in reason
        with _staging_connection(_ROOT) as connection:
            assert connection.execute("SELECT count(*) FROM arkkan.resource_definitions").fetchone() == (0,)
    finally:
        with _staging_connection(_ROOT) as connection, connection.transaction():
            connection.execute("DROP TRIGGER cli_test_failure ON arkkan.resource_versions")
            connection.execute("DROP FUNCTION public.cli_test_failure() RESTRICT")
    _json(cli("resource", "add", "rollback", "v", "-t", "task", "-j"), "add_resource")

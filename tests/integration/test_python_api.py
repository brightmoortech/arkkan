"""S4-030–035: real Python API calls in guarded staging with temporary logins."""

from collections.abc import Callable, Iterator
import os
from pathlib import Path
from secrets import token_urlsafe
from types import SimpleNamespace
from typing import Any

import psycopg
from psycopg import sql
import pytest

import arkkan
from arkkan import _api
from arkkan._provisioning import _load_settings
from arkkan._test_safety import _staging_connection
from test_db_initialization import _reset_application, _run

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Callable[..., dict]]:
    _reset_application()
    connections: list[psycopg.Connection] = []
    try:
        _run(apply=True)
        settings = _load_settings(_ROOT)
        password_file = tmp_path / "pgpass"
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
        # Create protected from the outset; never alter operator credential files.
        descriptor = password_file.open("x", opener=lambda path, flags: os.open(
            path, flags, 0o600))
        with descriptor:
            descriptor.write("\n".join(entries) + "\n")
        for name in ("PGHOST", "PGPORT", "PGDATABASE"):
            monkeypatch.setenv(name, settings[name])
        monkeypatch.setenv("PGPASSFILE", str(password_file))

        def connect(**kwargs: Any) -> psycopg.Connection:
            assert kwargs == {
                "host": settings["PGHOST"], "port": settings["PGPORT"],
                "dbname": settings["PGDATABASE"], "user": kwargs["user"],
                "passfile": str(password_file), "autocommit": False,
            }
            assert kwargs["user"] in {"arkkan_admin", "arkkan_user"}
            with _staging_connection(_ROOT):
                result = psycopg.connect(**kwargs)
            connections.append(result)
            return result

        # Patch only the boundary's driver reference, keeping guard connections real.
        monkeypatch.setattr(_api, "psycopg", SimpleNamespace(
            connect=connect, Error=psycopg.Error, OperationalError=psycopg.OperationalError,
            errors=psycopg.errors,
        ))

        def invoke(name: str, *args: Any, role: str = "arkkan_admin", **kwargs: Any) -> dict:
            monkeypatch.setenv("PGUSER", role)
            response = getattr(arkkan, name)(*args, **kwargs)
            assert response["operation_name"] == name
            assert response["message_type"] == "response"
            expected = {"operation_name", "message_type", "result"}
            if response["result"] == "success":
                assert set(response) == expected | {"data"}
            else:
                assert response["result"] == "error"
                assert set(response) == expected | {"reason"}
                assert isinstance(response["reason"], str) and response["reason"].strip()
            assert all(connection.closed for connection in connections)
            return response

        yield invoke
    finally:
        for connection in connections:
            connection.close()
        _reset_application()


def _success(response: dict) -> Any:
    assert response["result"] == "success", response
    return response["data"]


def test_s4_030_write_and_read_contracts(api: Callable[..., dict]) -> None:
    _success(api("add_resource_type", "custom", "original"))
    _success(api("update_resource_type", "custom", None))
    _success(api("add_resource", " r ☃ '; -- ", "v1", "custom", "Name", "Description",
                 "", "initial", "enabled_default"))
    slug = " r ☃ '; -- "
    _success(api("add_resource", slug, "v2", content="second", state="enabled"))
    changes = {"name": "", "description": None, "version_info": "revised"}
    _success(api("update_resource", slug, changes, version="v2"))
    assert changes == {"name": "", "description": None, "version_info": "revised"}
    for role in ("arkkan_admin", "arkkan_user"):
        for args, version, content in [((slug,), "v1", ""), ((slug, "v2"), "v2", "second"),
                                       ((slug, "v2", "strict"), "v2", "second"),
                                       ((slug, "missing", "version_priority"), "v1", ""),
                                       ((slug, "v2", "default_priority"), "v1", "")]:
            data = _success(api("get_resource_content", *args, role=role))
            assert data["version"] == version and data["content"] == content
        data = _success(api("get_resource_info", slug, role=role))
        assert data["name"] == "" and data["description"] is None
        assert "content" not in data
        assert _success(api("get_resource_version_default", slug, role=role))["version"] == "v1"
        assert len(_success(api("list_resources_matching_type", "custom", role=role))) == 1
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("SELECT description FROM arkkan.resource_types WHERE slug='custom'").fetchone() == (None,)
        assert connection.execute("SELECT version_info FROM arkkan.resource_versions WHERE version='v2'").fetchone() == ("revised",)


def test_s4_031_lifecycle_and_deletion(api: Callable[..., dict]) -> None:
    _success(api("add_resource_type", "custom"))
    _success(api("add_resource", "r", "v1", "custom", state="enabled_default"))
    _success(api("add_resource", "r", "v2", state="disabled"))
    assert api("set_resource_state", "r", "v1", "disabled")["result"] == "error"
    _success(api("set_resource_state", "r", "v1", "disabled", force=True))
    assert _success(api("set_resource_state_all", "r", "obsolete"))["changed_count"] == 2
    assert _success(api("delete_resource_version", "r", "v1"))["version"] == "v1"
    assert _success(api("delete_resource_version_all", "r"))["deleted_count"] == 1
    assert _success(api("delete_resource_version_all", "r"))["deleted_count"] == 0
    assert _success(api("get_resource_info", "r"))["versions"] == []
    assert _success(api("set_resource_state_all", "r", "disabled"))["changed_count"] == 0
    _success(api("add_resource", "r", "v3"))
    assert _success(api("set_resource_state_all_with_guard", "r", "disabled", "obsolete"))["changed_count"] == 1
    assert _success(api("set_resource_state_all_with_guard", "r", "enabled", "disabled"))["changed_count"] == 0
    assert _success(api("clean_up"))["deleted_count"] == 1
    assert _success(api("clean_up"))["deleted_count"] == 0
    assert _success(api("delete_resource", "r"))["deleted_version_count"] == 0
    _success(api("delete_resource_type", "custom"))


def test_s4_032_reader_cannot_write(api: Callable[..., dict]) -> None:
    calls = {
        "add_resource_type": ("custom",), "update_resource_type": ("task", "changed"),
        "delete_resource_type": ("task",), "add_resource": ("r", "v", "task"),
        "update_resource": ("r", {"name": "changed"}),
        "delete_resource_version": ("r", "v"), "delete_resource_version_all": ("r",),
        "delete_resource": ("r",), "clean_up": (),
        "set_resource_state": ("r", "v", "disabled"),
        "set_resource_state_all": ("r", "disabled"),
        "set_resource_state_all_with_guard": ("r", "enabled", "disabled"),
    }
    for name, args in calls.items():
        response = api(name, *args, role="arkkan_user")
        assert response["result"] == "error" and response["reason"].startswith("Access denied.")
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("SELECT count(*) FROM arkkan.resource_definitions").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM arkkan.resource_types").fetchone() == (7,)


def test_s4_033_invalid_calls_preserve_data(api: Callable[..., dict]) -> None:
    _success(api("add_resource", "r", "v", "task", state="enabled_default"))
    calls = [
        ("add_resource_type", ("task",)), ("update_resource_type", ("missing", "x")),
        ("delete_resource_type", ("task",)), ("add_resource", ("r", "v")),
        ("update_resource", ("r", {"name": "changed", "content": "secret"})),
        ("get_resource_content", ("r", None)), ("get_resource_content", ("r", "v", "bad")),
        ("get_resource_info", ("missing",)), ("get_resource_version_default", ("missing",)),
        ("list_resources_matching_type", (None,)),
        ("delete_resource_version", ("r", "v")), ("delete_resource_version_all", ("missing",)),
        ("delete_resource", ("r",)), ("set_resource_state", ("r", "v", "disabled", None)),
        ("set_resource_state_all", ("r", "disabled")),
        ("set_resource_state_all_with_guard", ("r", "enabled_default", "disabled")),
    ]
    before = _success(api("get_resource_info", "r"))
    for name, args in calls:
        response = api(name, *args)
        assert response["result"] == "error" and "secret" not in response["reason"]
    assert _success(api("get_resource_info", "r")) == before


def test_s4_034_failure_rolls_back(api: Callable[..., dict]) -> None:
    with _staging_connection(_ROOT) as connection:
        connection.execute("""CREATE FUNCTION public.python_test_failure() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'private diagnostic'; END $$""")
        connection.execute("""CREATE TRIGGER python_test_failure BEFORE INSERT ON
            arkkan.resource_versions FOR EACH ROW EXECUTE FUNCTION public.python_test_failure()""")
    try:
        response = api("add_resource", "rollback", "v", "task")
        assert response["result"] == "error"
        assert "private diagnostic" not in response["reason"]
        with _staging_connection(_ROOT) as connection:
            assert connection.execute("SELECT count(*) FROM arkkan.resource_definitions").fetchone() == (0,)
    finally:
        with _staging_connection(_ROOT) as connection:
            connection.execute("DROP TRIGGER python_test_failure ON arkkan.resource_versions")
            connection.execute("DROP FUNCTION public.python_test_failure() RESTRICT")
    _success(api("add_resource", "rollback", "v", "task"))


def test_s4_035_connection_failure(api: Callable[..., dict]) -> None:
    with _staging_connection(_ROOT) as connection:
        connection.execute("ALTER ROLE arkkan_user NOLOGIN")
    response = api("get_resource_info", "r", role="arkkan_user")
    assert response["result"] == "error"
    assert response["reason"] == (
        "Database connection or operation failed. Check connection settings, "
        "credentials and server availability."
    )
    with _staging_connection(_ROOT) as connection:
        connection.execute("ALTER ROLE arkkan_user LOGIN")
    assert api("get_resource_info", "r", role="arkkan_user")["reason"] == "Resource does not exist."

"""Application database foundation tests; run only in verified staging."""

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from arkkan._db_migrations import _API_WRITES, _PUBLIC_FUNCTIONS, _migration_list
from arkkan._migration_workflow import _Migration, _run_migrations
from arkkan._test_safety import _staging_connection

if TYPE_CHECKING:
    from psycopg import Connection

_ROOT = Path(__file__).resolve().parents[2]
_LOCK = int.from_bytes(b"arkkanDB", "big", signed=True)
_TABLES = ("resource_versions", "resource_definitions", "resource_types")


def _reset_application() -> None:
    """Reset only known application objects; never cascade to other schemas."""
    from psycopg import sql

    with _staging_connection(_ROOT) as connection:
        with connection.transaction():
            for name, arguments, _ in reversed(_PUBLIC_FUNCTIONS):
                signature = ", ".join(kind for _, kind in arguments)
                connection.execute(
                    f"DROP FUNCTION IF EXISTS arkkan_api.{name}({signature}) RESTRICT"
                )
            for table in _TABLES:
                connection.execute(sql.SQL("DROP TABLE IF EXISTS {}.{} RESTRICT").format(
                    sql.Identifier("arkkan"), sql.Identifier(table)))
                connection.execute(sql.SQL("DROP FUNCTION IF EXISTS {}.{}() RESTRICT").format(
                    sql.Identifier("arkkan"), sql.Identifier(f"reject_{table}_change")))
            for signature in (
                "api_response(text, text, jsonb, text)",
                "api_identifier_valid(text)", "api_state_valid(text)", "api_mode_valid(text)",
                "api_transition_valid(text, text)", "api_set_states(text, text, text, text)",
            ):
                # All signatures are fixed test-owned identifiers, never caller inputs.
                connection.execute(f"DROP FUNCTION IF EXISTS arkkan.{signature} RESTRICT")
            connection.execute("DROP SCHEMA IF EXISTS arkkan_api RESTRICT")
            connection.execute("DROP SCHEMA IF EXISTS arkkan RESTRICT")
            connection.execute("DROP ROLE IF EXISTS arkkan_admin")
            connection.execute("DROP ROLE IF EXISTS arkkan_user")


@pytest.fixture
def _clean_application() -> Iterator[None]:
    _reset_application()
    try:
        yield
    finally:
        _reset_application()


def _run(*, apply: bool) -> list[str]:
    messages: list[str] = []
    with _staging_connection(_ROOT) as connection:
        _run_migrations(connection, _migration_list(_ROOT), apply=apply,
                        lock_key=_LOCK, report=messages.append)
    return messages


@pytest.fixture
def _initialized(_clean_application: None) -> None:
    _run(apply=True)


def _state(connection: "Connection[Any]") -> tuple[Any, ...]:
    schemas = connection.execute("""
        SELECT nspname, oid FROM pg_catalog.pg_namespace
        WHERE nspname IN ('arkkan', 'arkkan_api') ORDER BY nspname
    """).fetchall()
    roles = connection.execute("""
        SELECT rolname, oid FROM pg_catalog.pg_roles
        WHERE rolname IN ('arkkan_admin', 'arkkan_user') ORDER BY rolname
    """).fetchall()
    identity = connection.execute("""
        SELECT singleton, environment_type FROM arkkan_env.environment_identity
    """).fetchall()
    relations = connection.execute("""
        SELECT n.nspname, c.relname, c.oid FROM pg_catalog.pg_class AS c
        JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('arkkan', 'arkkan_api') ORDER BY n.nspname, c.relname
    """).fetchall()
    functions = connection.execute("""
        SELECT n.nspname, p.proname, p.oid FROM pg_catalog.pg_proc AS p
        JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
        WHERE n.nspname IN ('arkkan', 'arkkan_api') ORDER BY n.nspname, p.proname, p.oid
    """).fetchall()
    return schemas, roles, identity, relations, functions


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    # Reverify the target immediately before starting a subprocess that can
    # connect or change the staging database.
    with _staging_connection(_ROOT):
        return subprocess.run([sys.executable, "scripts/init_db.py", *args],
                              cwd=_ROOT, text=True, capture_output=True, check=False)


def test_s2_060_clean_initialization_and_dry_run(_clean_application: None) -> None:
    with _staging_connection(_ROOT) as connection:
        before = _state(connection)
        assert before[0] == [] and before[1] == [] and before[3] == [] and before[4] == []
    for args in ((), ("--check",)):
        result = _cli(*args)
        assert result.returncode == 0, result.stderr
        assert result.stdout.count("[PENDING]") == 36
        assert "[APPLIED]" not in result.stdout
        with _staging_connection(_ROOT) as connection:
            assert _state(connection) == before
    result = _cli("--apply")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("[APPLIED]") == 36
    with _staging_connection(_ROOT) as connection:
        after = _state(connection)
        assert after[2] == before[2] == [(True, "staging")]
        assert {name for name, _ in after[0]} == {"arkkan", "arkkan_api"}
        assert {name for name, _ in after[1]} == {"arkkan_admin", "arkkan_user"}
        assert connection.execute("""
            SELECT c.relname FROM pg_catalog.pg_class AS c
            JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = 'arkkan' AND c.relkind = 'r' ORDER BY c.relname
        """).fetchall() == [(name,) for name in sorted(_TABLES)]
        assert connection.execute("""
            SELECT COUNT(*) FROM pg_catalog.pg_proc AS p
            JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
            WHERE n.nspname = 'arkkan_api'
        """).fetchone() == (18,)
        seeds = json.loads((_ROOT / "sql/migrations/012_resource_types.json").read_text())
        assert connection.execute("""
            SELECT slug, description, is_system FROM arkkan.resource_types ORDER BY slug
        """).fetchall() == [(slug, seeds[slug], True) for slug in sorted(seeds)]
    result = _cli("--apply")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("[UNCHANGED]") == 36
    assert "[APPLIED]" not in result.stdout
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == after


def test_s2_061_seed_reconciliation_preserves_metadata(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        type_id = connection.execute("""
            UPDATE arkkan.resource_types SET description = NULL WHERE slug = 'role'
            RETURNING type_id
        """).fetchone()[0]
        # Privileged staging operator simulates missing seed and custom data.
        connection.execute("DELETE FROM arkkan.resource_types WHERE slug = 'extensions'")
        custom_id = connection.execute("""
            INSERT INTO arkkan.resource_types (slug, description, is_system)
            VALUES ('custom', 'custom description', FALSE) RETURNING type_id
        """).fetchone()[0]
    report = _run(apply=True)
    assert [line for line in report if line.startswith("[APPLIED]")] == [
        "[APPLIED] 012_seed_resource_types"
    ]
    with _staging_connection(_ROOT) as connection:
        assert connection.execute("""
            SELECT type_id, description FROM arkkan.resource_types WHERE slug = 'role'
        """).fetchone() == (type_id, None)
        assert connection.execute("""
            SELECT type_id, description, is_system FROM arkkan.resource_types WHERE slug = 'custom'
        """).fetchone() == (custom_id, "custom description", False)
        assert connection.execute("""
            SELECT description, is_system FROM arkkan.resource_types WHERE slug = 'extensions'
        """).fetchone() == ("A generic catch-all extension to the prompt.", True)


def _records(connection: "Connection[Any]") -> tuple[Any, Any, Any]:
    type_id = connection.execute("""
        INSERT INTO arkkan.resource_types (slug, is_system) VALUES ('custom', FALSE)
        RETURNING type_id
    """).fetchone()[0]
    resource_id = connection.execute("""
        INSERT INTO arkkan.resource_definitions (slug, type_id) VALUES ('resource', %s)
        RETURNING resource_id
    """, (type_id,)).fetchone()[0]
    version_id, content, created_at = connection.execute("""
        INSERT INTO arkkan.resource_versions (resource_id, version, state)
        VALUES (%s, 'opaque-version', 'enabled_default')
        RETURNING version_id, content, created_at
    """, (resource_id,)).fetchone()
    assert content == "" and created_at.tzinfo is not None
    return type_id, resource_id, version_id


def test_s2_062_schema_constraints(_initialized: None) -> None:
    from psycopg.errors import CheckViolation, ForeignKeyViolation, NotNullViolation, UniqueViolation

    with _staging_connection(_ROOT) as connection:
        with connection.transaction(force_rollback=True):
            type_id, resource_id, _ = _records(connection)
            # Case and surrounding nonblank whitespace remain literal identifiers.
            connection.execute("""
                INSERT INTO arkkan.resource_types (slug, is_system)
                VALUES ('Custom', FALSE), (' custom ', FALSE)
            """)
            cases = (
                ("INSERT INTO arkkan.resource_types (slug, is_system) VALUES ('custom', FALSE)", (), UniqueViolation),
                ("INSERT INTO arkkan.resource_types (slug, is_system) VALUES (%s, FALSE)", (" \t\n",), CheckViolation),
                ("INSERT INTO arkkan.resource_types (slug, is_system) VALUES (NULL, FALSE)", (), NotNullViolation),
                ("INSERT INTO arkkan.resource_definitions (slug, type_id) VALUES ('resource', %s)", (type_id,), UniqueViolation),
                ("INSERT INTO arkkan.resource_definitions (slug, type_id) VALUES (' ', %s)", (type_id,), CheckViolation),
                ("INSERT INTO arkkan.resource_definitions (slug, type_id) VALUES ('other', %s)", (uuid4(),), ForeignKeyViolation),
                ("DELETE FROM arkkan.resource_types WHERE type_id = %s", (type_id,), ForeignKeyViolation),
                ("DELETE FROM arkkan.resource_definitions WHERE resource_id = %s", (resource_id,), ForeignKeyViolation),
                ("INSERT INTO arkkan.resource_versions (resource_id, version, state) VALUES (%s, 'opaque-version', 'disabled')", (resource_id,), UniqueViolation),
                ("INSERT INTO arkkan.resource_versions (resource_id, version, state) VALUES (%s, 'another', 'enabled_default')", (resource_id,), UniqueViolation),
                ("INSERT INTO arkkan.resource_versions (resource_id, version, state) VALUES (%s, %s, 'disabled')", (resource_id, "\t"), CheckViolation),
                ("INSERT INTO arkkan.resource_versions (resource_id, version, state) VALUES (%s, 'another', 'invalid')", (resource_id,), CheckViolation),
                ("INSERT INTO arkkan.resource_versions (resource_id, version, state, content) VALUES (%s, 'another', 'disabled', NULL)", (resource_id,), NotNullViolation),
                ("INSERT INTO arkkan.resource_versions (resource_id, version, state) VALUES (%s, 'another', 'disabled')", (uuid4(),), ForeignKeyViolation),
            )
            for statement, params, error in cases:
                with connection.transaction(force_rollback=True):
                    with pytest.raises(error):
                        connection.execute(statement, params)
            for state in ("enabled", "disabled", "obsolete"):
                connection.execute("""
                    INSERT INTO arkkan.resource_versions (resource_id, version, state)
                    VALUES (%s, %s, %s)
                """, (resource_id, state, state))


def test_s2_063_immutability_and_editable_fields(_initialized: None) -> None:
    from psycopg.errors import RaiseException

    with _staging_connection(_ROOT) as connection:
        with connection.transaction(force_rollback=True):
            type_id, resource_id, version_id = _records(connection)
            changes = (
                ("resource_types", "type_id", "gen_random_uuid()", "type_id", type_id),
                ("resource_types", "slug", "'changed'", "type_id", type_id),
                ("resource_types", "is_system", "TRUE", "type_id", type_id),
                ("resource_definitions", "resource_id", "gen_random_uuid()", "resource_id", resource_id),
                ("resource_definitions", "slug", "'changed'", "resource_id", resource_id),
                ("resource_definitions", "type_id", "gen_random_uuid()", "resource_id", resource_id),
                ("resource_versions", "version_id", "gen_random_uuid()", "version_id", version_id),
                ("resource_versions", "resource_id", "gen_random_uuid()", "version_id", version_id),
                ("resource_versions", "version", "'changed'", "version_id", version_id),
                ("resource_versions", "content", "'changed'", "version_id", version_id),
                ("resource_versions", "created_at", "created_at + interval '1 second'", "version_id", version_id),
            )
            # All identifiers and expressions are fixed test inputs, not user input.
            for table, column, expression, key, identifier in changes:
                with connection.transaction(force_rollback=True):
                    with pytest.raises(RaiseException, match="Immutable resource field"):
                        connection.execute(
                            f"UPDATE arkkan.{table} SET {column} = {expression} WHERE {key} = %s",
                            (identifier,))
            with connection.transaction(force_rollback=True):
                with pytest.raises(RaiseException, match="Immutable resource field"):
                    connection.execute("UPDATE arkkan.resource_types SET is_system = FALSE WHERE slug = 'role'")
            connection.execute("UPDATE arkkan.resource_types SET description = 'edited' WHERE type_id = %s", (type_id,))
            connection.execute("UPDATE arkkan.resource_definitions SET name = 'name', description = '' WHERE resource_id = %s", (resource_id,))
            connection.execute("UPDATE arkkan.resource_versions SET version_info = 'edited' WHERE version_id = %s", (version_id,))
            assert connection.execute("SELECT description FROM arkkan.resource_types WHERE type_id = %s", (type_id,)).fetchone() == ("edited",)
            assert connection.execute("SELECT name, description FROM arkkan.resource_definitions WHERE resource_id = %s", (resource_id,)).fetchone() == ("name", "")
            assert connection.execute("SELECT version_info, content FROM arkkan.resource_versions WHERE version_id = %s", (version_id,)).fetchone() == ("edited", "")


@pytest.mark.parametrize("role", ["arkkan_admin", "arkkan_user"])
def test_s2_064_application_roles_have_no_direct_access(_initialized: None, role: str) -> None:
    from psycopg import sql
    from psycopg.errors import InsufficientPrivilege

    with _staging_connection(_ROOT) as connection:
        assert connection.execute("""
            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
            FROM pg_catalog.pg_roles WHERE rolname = %s
        """, (role,)).fetchone() == (True, False, False, False, False, False)
        for table in _TABLES:
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
                assert connection.execute("SELECT pg_catalog.has_table_privilege(%s, %s, %s)",
                                          (role, f"arkkan.{table}", privilege)).fetchone() == (False,)
            assert connection.execute("SELECT pg_catalog.has_function_privilege(%s, %s, 'EXECUTE')",
                                      (role, f"arkkan.reject_{table}_change()")).fetchone() == (False,)
        with connection.transaction(force_rollback=True):
            connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
            for statement in ("SELECT slug FROM arkkan.resource_types",
                              "DELETE FROM arkkan.resource_types WHERE slug = 'role'",
                              "CREATE TABLE arkkan.forbidden (id integer)"):
                with connection.transaction(force_rollback=True):
                    with pytest.raises(InsufficientPrivilege):
                        connection.execute(statement)


def test_s2_065_conflict_before_any_apply(_clean_application: None) -> None:
    with _staging_connection(_ROOT) as connection:
        connection.execute("CREATE SCHEMA arkkan_api")
        connection.execute("CREATE TABLE arkkan_api.unexpected (id integer)")
    try:
        for apply in (False, True):
            with pytest.raises(ValueError, match="Unexpected relation"):
                _run(apply=apply)
        with _staging_connection(_ROOT) as connection:
            assert _state(connection)[1] == []
            assert _state(connection)[0][0][0] == "arkkan_api"
            assert len(_state(connection)[0]) == 1
    finally:
        with _staging_connection(_ROOT) as connection:
            connection.execute("DROP TABLE arkkan_api.unexpected RESTRICT")


@pytest.mark.parametrize("statement,match", [
    ("ALTER TABLE arkkan.resource_types ADD COLUMN unexpected text", "column definitions"),
    ("ALTER TABLE arkkan.resource_types DROP CONSTRAINT resource_types_slug_nonblank", "constraints"),
    ("ALTER TABLE arkkan.resource_types DISABLE TRIGGER protect_resource_types_immutable", "integrity trigger"),
    ("GRANT SELECT ON arkkan.resource_types TO PUBLIC", "privileges"),
    ("ALTER ROLE arkkan_user NOLOGIN", "attributes"),
    ("INSERT INTO arkkan.resource_types (slug, is_system) VALUES ('unexpected_system', TRUE)", "system resource type"),
])
def test_s2_066_existing_definition_conflicts(_initialized: None, statement: str, match: str) -> None:
    with _staging_connection(_ROOT) as connection:
        connection.execute(statement)
        before = _state(connection)
    for apply in (False, True):
        with pytest.raises(ValueError, match=match):
            _run(apply=apply)
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == before


def test_s2_067_actual_step_rollback(_clean_application: None) -> None:
    from psycopg import sql

    schema = "arkkan_init_rollback_" + uuid4().hex
    identifier = sql.Identifier(schema)

    def _schema_ready(connection: "Connection[Any]") -> bool:
        return bool(connection.execute("SELECT pg_catalog.to_regnamespace(%s) IS NOT NULL", (schema,)).fetchone()[0])

    def _schema_apply(connection: "Connection[Any]") -> None:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(identifier))

    def _fail(connection: "Connection[Any]") -> None:
        connection.execute(sql.SQL("CREATE TABLE {}.marker (id integer)").format(identifier))
        raise ValueError("Injected failure after DDL")

    def _later(connection: "Connection[Any]") -> None:
        connection.execute(sql.SQL("CREATE TABLE {}.later (id integer)").format(identifier))

    def _missing(connection: "Connection[Any]") -> bool:
        return False

    try:
        with _staging_connection(_ROOT) as connection:
            with pytest.raises(ValueError, match="Injected failure"):
                _run_migrations(connection, [
                    _Migration("first", _schema_ready, _schema_apply),
                    _Migration("failed", _missing, _fail),
                    _Migration("later", _missing, _later),
                ], apply=True, lock_key=_LOCK)
        with _staging_connection(_ROOT) as connection:
            assert _schema_ready(connection)
            for table in ("marker", "later"):
                assert connection.execute("SELECT pg_catalog.to_regclass(%s)", (f"{schema}.{table}",)).fetchone() == (None,)
    finally:
        with _staging_connection(_ROOT) as connection:
            with connection.transaction():
                for table in ("marker", "later"):
                    connection.execute(sql.SQL("DROP TABLE IF EXISTS {}.{} RESTRICT").format(identifier, sql.Identifier(table)))
                connection.execute(sql.SQL("DROP SCHEMA IF EXISTS {} RESTRICT").format(identifier))


def test_s3_001_response_contract(_initialized: None) -> None:
    from psycopg.types.json import Jsonb

    with _staging_connection(_ROOT) as connection:
        for data in ({"content": "", "optional": None}, [], [{"slug": "x"}]):
            response = connection.execute(
                "SELECT arkkan.api_response(%s, 'success', %s, NULL)",
                ("get_resource_content", Jsonb(data)),
            ).fetchone()[0]
            assert response == {"operation_name": "get_resource_content",
                                "message_type": "response", "result": "success", "data": data}
        response = connection.execute(
            "SELECT arkkan.api_response(%s, 'error', NULL, %s)",
            ("get_resource_content", "Requested resource version is unavailable."),
        ).fetchone()[0]
        assert response == {"operation_name": "get_resource_content", "message_type": "response",
                            "result": "error", "reason": "Requested resource version is unavailable."}


def test_s3_002_invalid_response_arguments(_initialized: None) -> None:
    from psycopg.errors import InvalidParameterValue
    from psycopg.types.json import Jsonb

    cases = (
        (None, "success", Jsonb({}), None), (" \t", "success", Jsonb({}), None),
        ("operation", None, Jsonb({}), None), ("operation", "unknown", Jsonb({}), None),
        ("operation", "success", None, None), ("operation", "success", Jsonb(None), None),
        ("operation", "success", Jsonb("secret"), None),
        ("operation", "success", Jsonb({}), "secret"),
        ("operation", "error", Jsonb({}), "secret"),
        ("operation", "error", None, None), ("operation", "error", None, " \t\n"),
    )
    with _staging_connection(_ROOT) as connection:
        for arguments in cases:
            with pytest.raises(InvalidParameterValue) as error:
                with connection.transaction():
                    connection.execute("SELECT arkkan.api_response(%s, %s, %s::jsonb, %s)", arguments)
            assert "secret" not in str(error.value)


def test_s3_003_shared_validation(_initialized: None) -> None:
    cases = (
        ("api_identifier_valid", ("x", " x ", "X", "0"), (None, "", " \t\n")),
        ("api_state_valid", ("enabled", "enabled_default", "disabled", "obsolete"),
         (None, "", "Enabled", " enabled", "invalid")),
        ("api_mode_valid", ("strict", "version_priority", "default_priority"),
         (None, "", "Strict", " strict", "invalid")),
    )
    with _staging_connection(_ROOT) as connection:
        for name, valid, invalid in cases:
            for values, expected in ((valid, True), (invalid, False)):
                for value in values:
                    assert connection.execute(
                        f"SELECT arkkan.{name}(%s::text)", (value,)
                    ).fetchone() == (expected,)


@pytest.mark.parametrize("role", ["arkkan_admin", "arkkan_user"])
def test_s3_004_private_helpers_denied(_initialized: None, role: str) -> None:
    from psycopg import sql
    from psycopg.errors import InsufficientPrivilege

    with _staging_connection(_ROOT) as connection:
        for signature, arguments in (
            ("api_response(text, text, jsonb, text)", "'operation', 'success', '{}'::jsonb, NULL"),
            ("api_identifier_valid(text)", "'x'"),
            ("api_state_valid(text)", "'enabled'"),
            ("api_mode_valid(text)", "'strict'"),
        ):
            assert connection.execute(
                "SELECT pg_catalog.has_function_privilege(%s, %s, 'EXECUTE')",
                (role, f"arkkan.{signature}"),
            ).fetchone() == (False,)
            with pytest.raises(InsufficientPrivilege):
                with connection.transaction(force_rollback=True):
                    # Grant schema usage temporarily to test function ACL independently.
                    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA arkkan TO {}").format(sql.Identifier(role)))
                    connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                    connection.execute(f"SELECT arkkan.{signature.split('(')[0]}({arguments})")


@pytest.mark.parametrize("statement,cleanup", [
    ("ALTER FUNCTION arkkan.api_response(text,text,jsonb,text) SECURITY DEFINER", None),
    ("GRANT EXECUTE ON FUNCTION arkkan.api_response(text,text,jsonb,text) TO PUBLIC", None),
    ("CREATE FUNCTION arkkan.api_response(text,text,text,text) RETURNS jsonb LANGUAGE sql AS 'SELECT NULL::jsonb'",
     "DROP FUNCTION arkkan.api_response(text,text,text,text)"),
])
def test_s3_005_helper_conflict(_initialized: None, statement: str, cleanup: str | None) -> None:
    with _staging_connection(_ROOT) as connection:
        connection.execute(statement)
    try:
        for apply in (False, True):
            with pytest.raises(ValueError, match="Conflicting API function"):
                _run(apply=apply)
    finally:
        if cleanup is not None:
            with _staging_connection(_ROOT) as connection:
                connection.execute(cleanup)


def test_s3_007_upgrade_preserves_stage2_database(_clean_application: None) -> None:
    with _staging_connection(_ROOT) as connection:
        _run_migrations(connection, _migration_list(_ROOT)[:12], apply=True,
                        lock_key=_LOCK, report=lambda message: None)
        _records(connection)
        connection.execute("UPDATE arkkan.resource_types SET description = 'edited' WHERE slug = 'role'")
        before = _state(connection)
        queries = (
            "SELECT type_id, slug, description, is_system FROM arkkan.resource_types ORDER BY slug",
            "SELECT resource_id, name, slug, description, type_id FROM arkkan.resource_definitions ORDER BY slug",
            "SELECT version_id, resource_id, version, state, content, version_info, created_at "
            "FROM arkkan.resource_versions ORDER BY version_id",
        )
        data_before = [connection.execute(query).fetchall() for query in queries]
    plan = _run(apply=False)
    assert [line for line in plan if line.startswith("[PENDING]")] == [
        "[PENDING] 013_api_response", "[PENDING] 014_api_identifier_valid",
        "[PENDING] 015_api_state_valid", "[PENDING] 016_api_mode_valid",
        *[f"[PENDING] {step.name}" for step in _migration_list(_ROOT)[16:]],
    ]
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == before
        assert [connection.execute(query).fetchall() for query in queries] == data_before
    applied = _run(apply=True)
    assert [line for line in applied if line.startswith("[APPLIED]")] == [
        line.replace("[PENDING]", "[APPLIED]") for line in plan if line.startswith("[PENDING]")
    ]
    with _staging_connection(_ROOT) as connection:
        after = _state(connection)
        assert after[:4] == before[:4]
        assert set(before[4]).issubset(after[4]) and len(after[4]) == len(before[4]) + 24
        assert [connection.execute(query).fetchall() for query in queries] == data_before
    assert not any(line.startswith("[APPLIED]") for line in _run(apply=True))
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == after


def _call(connection: "Connection[Any]", name: str, *arguments: Any) -> dict[str, Any]:
    """Call only fixed WP2 function names and check their response envelope."""
    from psycopg import sql

    assert name in {item[0] for item in _PUBLIC_FUNCTIONS}
    response = connection.execute(
        sql.SQL("SELECT arkkan_api.{}({})").format(
            sql.Identifier(name), sql.SQL(", ").join(sql.Placeholder() for _ in arguments),
        ), arguments,
    ).fetchone()[0]
    assert response["operation_name"] == name and response["message_type"] == "response"
    assert response["result"] in ("success", "error")
    if response["result"] == "success":
        assert set(response) == {"operation_name", "message_type", "result", "data"}
        assert isinstance(response["data"], list if name == "list_resources_matching_type" else dict)
    else:
        assert set(response) == {"operation_name", "message_type", "result", "reason"}
        assert isinstance(response["reason"], str) and response["reason"].strip()
    return response


def _snapshot(connection: "Connection[Any]") -> list[list[Any]]:
    return [connection.execute(query).fetchall() for query in (
        "SELECT type_id, slug, description, is_system FROM arkkan.resource_types ORDER BY slug",
        "SELECT resource_id, slug, name, description, type_id FROM arkkan.resource_definitions ORDER BY slug",
        "SELECT version_id, resource_id, version, state, content, version_info, created_at "
        "FROM arkkan.resource_versions ORDER BY version_id",
    )]


def test_s3_009_type_write_contracts(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        result = _call(connection, "add_resource_type", " Custom ")
        assert result["result"] == "success"
        assert set(result["data"]) == {"type_id", "slug"}
        assert result["data"]["slug"] == " Custom "
        from uuid import UUID
        UUID(result["data"]["type_id"])
        assert connection.execute(
            "SELECT description, is_system FROM arkkan.resource_types WHERE slug = ' Custom '"
        ).fetchone() == (None, False)
        assert _call(connection, "add_resource_type", "custom", "description")["result"] == "success"
        for slug in ("custom", "role"):
            for description in ("edited", "", None):
                result = _call(connection, "update_resource_type", slug, description)
                assert result["data"] == {"slug": slug, "description": description}
                assert connection.execute(
                    "SELECT description FROM arkkan.resource_types WHERE slug = %s", (slug,)
                ).fetchone() == (description,)
        assert _call(connection, "delete_resource_type", "custom")["data"] == {"slug": "custom"}
        assert connection.execute(
            "SELECT count(*) FROM arkkan.resource_types WHERE slug = 'custom'"
        ).fetchone() == (0,)


def test_s3_010_invalid_type_writes_preserve_data(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        before = _snapshot(connection)
        for name, args in (
            ("add_resource_type", ("role",)),
            ("update_resource_type", ("missing", "new")),
            ("delete_resource_type", ("missing",)),
            *[("delete_resource_type", (slug,)) for slug in (
                "constraints", "process", "rubric", "role", "task", "templates", "extensions",
            )],
            *[(name, (slug, None) if name == "update_resource_type" else (slug,))
              for name in ("add_resource_type", "update_resource_type", "delete_resource_type")
              for slug in (None, "", " \t\n")],
        ):
            assert _call(connection, name, *args)["result"] == "error"
            assert _snapshot(connection) == before


def test_s3_011_referenced_type_deletion_denied(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        _records(connection)
        for empty in (False, True):
            if empty:
                connection.execute("DELETE FROM arkkan.resource_versions")
            before = _snapshot(connection)
            assert _call(connection, "delete_resource_type", "custom")["result"] == "error"
            assert _snapshot(connection) == before


def test_s3_012_add_resource_contract(_initialized: None) -> None:
    from datetime import datetime, timezone
    from uuid import UUID

    with _staging_connection(_ROOT) as connection:
        connection.execute("SET TIME ZONE 'Pacific/Auckland'")
        result = _call(connection, "add_resource", " Resource ", "version-z", "role", "Name", "Description")
        assert result["result"] == "success"
        data = result["data"]
        assert set(data) == {"resource_id", "version_id", "slug", "version", "state", "created_at"}
        UUID(data["resource_id"])
        UUID(data["version_id"])
        assert (data["slug"], data["version"], data["state"]) == (" Resource ", "version-z", "disabled")
        assert data["created_at"].endswith("Z")
        row = connection.execute(
            "SELECT content, version_info, created_at FROM arkkan.resource_versions WHERE version_id = %s",
            (data["version_id"],),
        ).fetchone()
        assert row[:2] == ("", None)
        assert datetime.fromisoformat(data["created_at"]) == row[2].astimezone(timezone.utc)
        for version, state in (("2", "enabled"), ("1", "enabled_default"), ("0", "enabled_default")):
            result = _call(connection, "add_resource", " Resource ", version, "role",
                           "Ignored", "Ignored", "body\n", "info", state)
            assert result["result"] == "success"
            assert result["data"]["resource_id"] == data["resource_id"]
        assert _call(connection, "add_resource", " Resource ", "no-type")["result"] == "success"
        assert connection.execute(
            "SELECT name, description FROM arkkan.resource_definitions WHERE slug = ' Resource '"
        ).fetchone() == ("Name", "Description")
        assert connection.execute(
            "SELECT version, state FROM arkkan.resource_versions WHERE state IN ('enabled', 'enabled_default') "
            "ORDER BY version"
        ).fetchall() == [("0", "enabled_default"), ("1", "enabled"), ("2", "enabled")]
        assert connection.execute(
            "SELECT content, version_info FROM arkkan.resource_versions WHERE version = '0'"
        ).fetchone() == ("body\n", "info")


def test_s3_013_invalid_add_resource_preserves_data(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        assert _call(connection, "add_resource", "existing", "v", "role")["result"] == "success"
        before = _snapshot(connection)
        cases = [
            ("new", "v"), ("new", "v", "missing"), ("existing", "other", "task"),
            ("existing", "v", None, None, None, "private-content", None, "enabled_default"),
            ("new", "v", "role", None, None, None),
        ]
        for slug in (None, "", " \t\n"):
            cases.extend([(slug, "v", "role"), ("new", slug, "role"), ("new", "v", slug)])
        for state in (None, "", "obsolete", "Enabled", " enabled", "unknown"):
            cases.append(("new", "v", "role", None, None, "private-content", None, state))
        for args in cases:
            result = _call(connection, "add_resource", *args)
            assert result["result"] == "error"
            assert "private-content" not in result["reason"]
            assert _snapshot(connection) == before


def test_s3_014_add_resource_rolls_back_after_write(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        assert _call(connection, "add_resource", "resource", "default", "role",
                     None, None, "", None, "enabled_default")["result"] == "success"
        with connection.transaction(force_rollback=True):
            # Inject a specific expected database failure after the function has
            # demoted the old default or created a new definition.
            connection.execute("""
                CREATE FUNCTION pg_temp.reject_test_insert() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                    RAISE EXCEPTION 'synthetic sensitive diagnostic' USING ERRCODE = '23505';
                END $$
            """)
            connection.execute("""
                CREATE TRIGGER test_reject_insert BEFORE INSERT ON arkkan.resource_versions
                FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_test_insert()
            """)
            before = _snapshot(connection)
            for slug in ("resource", "new-resource"):
                result = _call(connection, "add_resource", slug, "new", "role",
                               None, None, "private-content", None, "enabled_default")
                assert result["result"] == "error"
                assert "sensitive" not in result["reason"] and "private-content" not in result["reason"]
                assert _snapshot(connection) == before


def test_s3_015_update_resource_contract(_initialized: None) -> None:
    from psycopg.types.json import Jsonb

    with _staging_connection(_ROOT) as connection:
        _records(connection)
        before = connection.execute(
            "SELECT version_id, resource_id, version, state, content, created_at FROM arkkan.resource_versions"
        ).fetchall()
        expected_metadata = {"name": None, "description": None, "version_info": None}
        for changes in ({"name": "New name"}, {"description": ""},
                        {"name": None, "description": None, "version_info": "Changes"},
                        {"version_info": ""}, {"version_info": None}):
            args = ("resource", Jsonb(changes))
            if "version_info" in changes:
                args += ("opaque-version",)
            result = _call(connection, "update_resource", *args)
            assert result["result"] == "success"
            expected = {"slug": "resource", "updated_fields": sorted(changes)}
            if "version_info" in changes:
                expected["version"] = "opaque-version"
            assert result["data"] == expected
            metadata = connection.execute(
                "SELECT d.name, d.description, v.version_info FROM arkkan.resource_definitions AS d "
                "JOIN arkkan.resource_versions AS v USING (resource_id) WHERE d.slug = 'resource'"
            ).fetchone()
            expected_metadata.update(changes)
            assert dict(zip(("name", "description", "version_info"), metadata)) == expected_metadata
            assert connection.execute(
                "SELECT version_id, resource_id, version, state, content, created_at FROM arkkan.resource_versions"
            ).fetchall() == before
        for state in ("enabled", "disabled", "obsolete"):
            connection.execute("UPDATE arkkan.resource_versions SET state = %s", (state,))
            result = _call(connection, "update_resource", "resource", Jsonb({"version_info": state}), "opaque-version")
            assert result["result"] == "success"
            assert connection.execute("SELECT state, version_info FROM arkkan.resource_versions").fetchone() == (state, state)
        connection.execute("DELETE FROM arkkan.resource_versions")
        assert _call(connection, "update_resource", "resource", Jsonb({"name": "Empty resource"}))["result"] == "success"


def test_s3_016_invalid_updates_are_atomic(_initialized: None) -> None:
    from psycopg.types.json import Jsonb

    with _staging_connection(_ROOT) as connection:
        _records(connection)
        before = _snapshot(connection)
        cases = [("resource", None), ("missing", Jsonb({"name": "x"})),
                 ("resource", Jsonb({"name": "x"}), "opaque-version"),
                 ("resource", Jsonb({"name": "x", "version_info": "x"}), "missing")]
        cases += [("resource", Jsonb(value)) for value in (None, {}, [], "text", 1, True)]
        cases += [(slug, Jsonb({"name": "x"})) for slug in (None, "", " \t")]
        cases += [("resource", Jsonb({"version_info": "x"}), version) for version in (None, "", " \n")]
        for key in ("slug", "type_slug", "version", "content", "state", "resource_id", "created_at", "unknown"):
            cases.append(("resource", Jsonb({"name": "x", key: "private-content"})))
        for key in ("name", "description", "version_info"):
            for value in (1, True, [], {}):
                cases.append(("resource", Jsonb({key: value}), "opaque-version" if key == "version_info" else None))
        for args in cases:
            result = _call(connection, "update_resource", *args)
            assert result["result"] == "error" and "private-content" not in result["reason"]
            assert _snapshot(connection) == before


@pytest.mark.parametrize("role", ["arkkan_admin", "arkkan_user"])
def test_s3_017_write_functions_restricted(_initialized: None, role: str) -> None:
    from psycopg import sql
    from psycopg.errors import InsufficientPrivilege

    with _staging_connection(_ROOT) as connection:
        for name, arguments, _ in _API_WRITES:
            signature = f"arkkan_api.{name}({', '.join(kind for _, kind in arguments)})"
            assert connection.execute(
                "SELECT pg_catalog.has_function_privilege(%s, %s, 'EXECUTE')", (role, signature)
            ).fetchone() == (False,)
            with pytest.raises(InsufficientPrivilege):
                with connection.transaction(force_rollback=True):
                    connection.execute(sql.SQL("GRANT USAGE ON SCHEMA arkkan_api TO {}").format(sql.Identifier(role)))
                    connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
                    connection.execute(f"SELECT arkkan_api.{name}({', '.join('NULL::' + kind for _, kind in arguments)})")
        # Verify SECURITY DEFINER execution without table/helper access. These
        # temporary admin grants roll back; permanent exposure belongs to WP5.
        if role == "arkkan_admin":
            with connection.transaction(force_rollback=True):
                connection.execute("GRANT USAGE ON SCHEMA arkkan_api TO arkkan_admin")
                for name, arguments, _ in _API_WRITES:
                    signature = f"arkkan_api.{name}({', '.join(kind for _, kind in arguments)})"
                    connection.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO arkkan_admin")
                connection.execute("SET LOCAL ROLE arkkan_admin")
                from psycopg.types.json import Jsonb
                for name, args in (
                    ("add_resource_type", ("admin-type",)),
                    ("update_resource_type", ("admin-type", "description")),
                    ("delete_resource_type", ("admin-type",)),
                    ("add_resource", ("admin-resource", "v", "role")),
                    ("update_resource", ("admin-resource", Jsonb({"name": "Name"}))),
                ):
                    assert _call(connection, name, *args)["result"] == "success"


@pytest.mark.parametrize("statement,cleanup", [
    ("ALTER FUNCTION arkkan_api.add_resource_type(text,text) SECURITY INVOKER", None),
    ("ALTER FUNCTION arkkan_api.add_resource_type(text,text) SET search_path = public", None),
    ("GRANT EXECUTE ON FUNCTION arkkan_api.add_resource_type(text,text) TO PUBLIC", None),
    ("CREATE FUNCTION arkkan_api.add_resource_type(text,integer) RETURNS jsonb LANGUAGE sql AS 'SELECT NULL::jsonb'",
     "DROP FUNCTION arkkan_api.add_resource_type(text,integer)"),
])
def test_s3_018_write_function_conflict(_initialized: None, statement: str, cleanup: str | None) -> None:
    with _staging_connection(_ROOT) as connection:
        connection.execute(statement)
        before = _state(connection)
    try:
        for apply in (False, True):
            with pytest.raises(ValueError, match="Conflicting API function"):
                _run(apply=apply)
        with _staging_connection(_ROOT) as connection:
            assert _state(connection) == before
    finally:
        if cleanup:
            with _staging_connection(_ROOT) as connection:
                connection.execute(cleanup)


def test_s3_019_upgrade_preserves_wp1(_clean_application: None) -> None:
    with _staging_connection(_ROOT) as connection:
        _run_migrations(connection, _migration_list(_ROOT)[:16], apply=True,
                        lock_key=_LOCK, report=lambda message: None)
        _records(connection)
        before_state, before_data = _state(connection), _snapshot(connection)
    plan = _run(apply=False)
    assert [line for line in plan if line.startswith("[PENDING]")] == [
        f"[PENDING] {step.name}" for step in _migration_list(_ROOT)[16:]
    ]
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == before_state and _snapshot(connection) == before_data
    _run(apply=True)
    with _staging_connection(_ROOT) as connection:
        after = _state(connection)
        assert after[:4] == before_state[:4]
        assert set(before_state[4]).issubset(after[4]) and len(after[4]) == len(before_state[4]) + 20
        assert _snapshot(connection) == before_data
    assert not any(line.startswith("[APPLIED]") for line in _run(apply=True))
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == after and _snapshot(connection) == before_data


@pytest.mark.parametrize("scenario", ["new-defaults", "existing-defaults", "duplicate", "type-delete", "different-types", "metadata"])
def test_s3_020_concurrent_writes(_initialized: None, scenario: str) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from psycopg.types.json import Jsonb

    with _staging_connection(_ROOT) as connection:
        assert _call(connection, "add_resource_type", "custom")["result"] == "success"
        if scenario in ("existing-defaults", "metadata"):
            assert _call(connection, "add_resource", "resource", "old", "custom",
                         None, None, "", None, "enabled_default")["result"] == "success"
    barrier = Barrier(2, timeout=10)

    def worker(index: int) -> dict[str, Any]:
        with _staging_connection(_ROOT) as connection:
            connection.execute("SET statement_timeout = '10s'")
            with connection.transaction():
                barrier.wait()
                if scenario == "type-delete" and index == 1:
                    return _call(connection, "delete_resource_type", "custom")
                if scenario == "metadata":
                    changes = {"name": "Name"} if index == 0 else {"description": "Description"}
                    return _call(connection, "update_resource", "resource", Jsonb(changes))
                version = "same" if scenario == "duplicate" else str(index)
                type_slug = "role" if scenario == "different-types" and index == 1 else "custom"
                return _call(connection, "add_resource", "resource", version, type_slug,
                             None, None, "", None, "enabled_default")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in range(2)]
        responses = [future.result(timeout=20) for future in futures]
    results = sorted(response["result"] for response in responses)
    if scenario in ("duplicate", "type-delete", "different-types"):
        assert results == ["error", "success"]
    else:
        assert results == ["success", "success"]
    with _staging_connection(_ROOT) as connection:
        versions = connection.execute("SELECT version, state FROM arkkan.resource_versions").fetchall()
        if scenario == "type-delete" and responses[1]["result"] == "success":
            assert versions == []
            assert connection.execute("SELECT count(*) FROM arkkan.resource_definitions").fetchone() == (0,)
        else:
            assert sum(state == "enabled_default" for _, state in versions) == 1
            assert len(versions) == {"new-defaults": 2, "existing-defaults": 3,
                                     "duplicate": 1, "type-delete": 1, "different-types": 1, "metadata": 1}[scenario]
        if scenario == "metadata":
            assert connection.execute(
                "SELECT name, description FROM arkkan.resource_definitions WHERE slug = 'resource'"
            ).fetchone() == ("Name", "Description")
        if scenario == "different-types":
            winner = next(index for index, result in enumerate(responses) if result["result"] == "success")
            assert connection.execute(
                "SELECT t.slug FROM arkkan.resource_definitions AS d "
                "JOIN arkkan.resource_types AS t USING (type_id) WHERE d.slug = 'resource'"
            ).fetchone() == (("custom", "role")[winner],)


@pytest.mark.parametrize("operation", ["add_resource", "update_resource"])
def test_s3_021_resource_writes_wait_for_lock(_initialized: None, operation: str) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from time import monotonic, sleep
    from psycopg.types.json import Jsonb

    backend: Queue[int] = Queue()

    def worker() -> dict[str, Any]:
        with _staging_connection(_ROOT) as connection:
            connection.execute("SET statement_timeout = '10s'")
            backend.put(connection.info.backend_pid)
            if operation == "add_resource":
                return _call(connection, operation, "resource", "next", None,
                             None, None, "", None, "enabled_default")
            return _call(connection, operation, "resource", Jsonb({"name": "Updated"}))

    with ThreadPoolExecutor(max_workers=1) as pool:
        with _staging_connection(_ROOT) as connection:
            _records(connection)
            with connection.transaction():
                connection.execute(
                    "SELECT resource_id FROM arkkan.resource_definitions "
                    "WHERE slug = 'resource' FOR UPDATE"
                )
                future = pool.submit(worker)
                pid = backend.get(timeout=10)
                deadline = monotonic() + 5
                while monotonic() < deadline:
                    blockers = connection.execute(
                        "SELECT pg_catalog.pg_blocking_pids(%s)", (pid,)
                    ).fetchone()[0]
                    if connection.info.backend_pid in blockers:
                        break
                    assert not future.done(), "Resource write bypassed the resource lock."
                    sleep(0.01)
                else:
                    pytest.fail("Resource write did not wait on the held resource lock.")
                assert not future.done()
            assert future.result(timeout=15)["result"] == "success"


def test_s3_022_content_selection_matrix(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        for state in (None, 'disabled', 'obsolete', 'enabled', 'enabled_default'):
            for default in (False, True):
                if state == 'enabled_default' and default:
                    continue
                with connection.transaction(force_rollback=True):
                    created = _call(connection, 'add_resource', 'resource', 'requested', 'role')
                    assert created['result'] == 'success'
                    if state is None:
                        connection.execute('DELETE FROM arkkan.resource_versions')
                    else:
                        connection.execute('UPDATE arkkan.resource_versions SET state = %s', (state,))
                    if default:
                        assert _call(connection, 'add_resource', 'resource', 'default', None,
                                     None, None, 'fallback', None, 'enabled_default')['result'] == 'success'
                    available = state in ('enabled', 'enabled_default')
                    default_version = 'default' if default else 'requested' if state == 'enabled_default' else None
                    for mode in ('strict', 'version_priority', 'default_priority'):
                        selected = ('requested' if available else None) if mode == 'strict' else (
                            ('requested' if available else default_version) if mode == 'version_priority'
                            else (default_version or ('requested' if available else None)))
                        result = _call(connection, 'get_resource_content', 'resource', 'requested', mode)
                        if selected is None:
                            assert result['result'] == 'error'
                        else:
                            assert result['data'] == {
                                'slug': 'resource', 'version': selected,
                                'state': 'enabled_default' if selected == default_version else state,
                                'content': 'fallback' if selected == 'default' else '',
                            }
                        if mode == 'strict':
                            assert _call(connection, 'get_resource_content', 'resource', 'requested') == result
                    result = _call(connection, 'get_resource_content', 'resource')
                    lookup = _call(connection, 'get_resource_version_default', 'resource')
                    if default_version is None:
                        assert result['result'] == lookup['result'] == 'error'
                    else:
                        assert result['data']['version'] == default_version
                        assert lookup['data'] == {'slug': 'resource', 'version': default_version}


def test_s3_023_read_metadata_and_validation(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        assert _call(connection, 'list_resources_matching_type', 'role')['data'] == []
        assert _call(connection, 'add_resource', 'r', 'v', 'role', 'Name', 'Description')['result'] == 'success'
        for version, state in (('e', 'enabled'), ('d', 'enabled_default'), ('o', 'disabled')):
            assert _call(connection, 'add_resource', 'r', version, None, None, None,
                         'sensitive-content', None, state)['result'] == 'success'
        connection.execute("UPDATE arkkan.resource_versions SET state = 'obsolete' WHERE version = 'o'")
        result = _call(connection, 'get_resource_info', 'r')
        assert set(result['data']) == {'slug', 'name', 'description', 'type_slug', 'versions'}
        assert result['data'] | {'versions': []} == {
            'slug': 'r', 'name': 'Name', 'description': 'Description', 'type_slug': 'role', 'versions': [],
        }
        assert {v['state'] for v in result['data']['versions']} == {'enabled', 'enabled_default', 'disabled', 'obsolete'}
        for version in result['data']['versions']:
            assert set(version) == {'version', 'state', 'created_at'} and version['created_at'].endswith('Z')
        assert 'sensitive-content' not in str(result)
        connection.execute('DELETE FROM arkkan.resource_versions')
        assert _call(connection, 'get_resource_info', 'r')['data']['versions'] == []
        assert _call(connection, 'list_resources_matching_type', 'role')['data'] == [
            {'slug': 'r', 'name': 'Name', 'description': 'Description'},
        ]
        for name in ('get_resource_info', 'get_resource_content', 'get_resource_version_default', 'list_resources_matching_type'):
            for value in (None, '', ' \t', 'missing'):
                assert _call(connection, name, value)['result'] == 'error'
        for version in (None, '', ' \n'):
            assert _call(connection, 'get_resource_content', 'r', version)['result'] == 'error'
        for mode in (None, '', 'Strict', 'unknown'):
            assert _call(connection, 'get_resource_content', 'r', 'v', mode)['result'] == 'error'


def test_s3_024_state_transition_matrix(_initialized: None) -> None:
    allowed = {
        'enabled': {'enabled_default', 'disabled'},
        'enabled_default': {'enabled', 'disabled'},
        'disabled': {'enabled', 'enabled_default', 'obsolete'},
        'obsolete': {'disabled'},
    }
    with _staging_connection(_ROOT) as connection:
        _records(connection)
        for source, targets in allowed.items():
            for target in allowed:
                for force in (False, True):
                    with connection.transaction(force_rollback=True):
                        connection.execute('UPDATE arkkan.resource_versions SET state = %s', (source,))
                        before = _snapshot(connection)
                        result = _call(connection, 'set_resource_state', 'resource', 'opaque-version', target, force)
                        success = target in targets and (source != 'enabled_default' or force)
                        assert result['result'] == ('success' if success else 'error')
                        if success:
                            assert result['data'] == {'slug': 'resource', 'version': 'opaque-version', 'state': target}
                            assert connection.execute('SELECT state FROM arkkan.resource_versions').fetchone() == (target,)
                        else:
                            assert _snapshot(connection) == before
        assert _call(connection, 'add_resource', 'resource', 'new')['result'] == 'success'
        assert _call(connection, 'set_resource_state', 'resource', 'new', 'enabled_default')['result'] == 'success'
        assert connection.execute('SELECT version, state FROM arkkan.resource_versions ORDER BY version').fetchall() == [
            ('new', 'enabled_default'), ('opaque-version', 'enabled'),
        ]
        for args in ((None, 'new', 'enabled'), ('resource', None, 'enabled'),
                     ('missing', 'new', 'enabled'), ('resource', 'missing', 'enabled'),
                     ('resource', 'new', None), ('resource', 'new', 'unknown'),
                     ('resource', 'new', 'disabled', None)):
            before = _snapshot(connection)
            assert _call(connection, 'set_resource_state', *args)['result'] == 'error'
            assert _snapshot(connection) == before


def test_s3_025_bulk_state_policy(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        _records(connection)
        assert _call(connection, 'add_resource', 'resource', 'second')['result'] == 'success'
        # A single enabled selection can replace a default. The demoted default
        # must not become a new member of that selection.
        connection.execute("UPDATE arkkan.resource_versions SET state = 'enabled' WHERE version = 'second'")
        result = _call(connection, 'set_resource_state_all_with_guard', 'resource', 'enabled', 'enabled_default')
        assert result['data'] == {'slug': 'resource', 'changed_count': 1}
        assert connection.execute('SELECT version, state FROM arkkan.resource_versions ORDER BY version').fetchall() == [
            ('opaque-version', 'enabled'), ('second', 'enabled_default'),
        ]
        for args in (('resource', 'disabled'), ('resource', 'enabled_default'), ('resource', 'enabled')):
            before = _snapshot(connection)
            assert _call(connection, 'set_resource_state_all', *args)['result'] == 'error'
            assert _snapshot(connection) == before
        connection.execute("UPDATE arkkan.resource_versions SET state = 'disabled'")
        before = _snapshot(connection)
        assert _call(connection, 'set_resource_state_all', 'resource', 'enabled_default')['result'] == 'error'
        assert _snapshot(connection) == before
        assert _call(connection, 'set_resource_state_all', 'resource', 'enabled')['data'] == {
            'slug': 'resource', 'changed_count': 2,
        }
        assert _call(connection, 'set_resource_state_all_with_guard', 'resource', 'obsolete', 'disabled')['data']['changed_count'] == 0
        before = _snapshot(connection)
        assert _call(connection, 'set_resource_state_all_with_guard', 'resource', 'enabled', 'enabled')['result'] == 'error'
        assert _snapshot(connection) == before
        assert _call(connection, 'set_resource_state_all', 'resource', 'disabled')['result'] == 'success'
        assert _call(connection, 'set_resource_state_all', 'resource', 'obsolete')['result'] == 'success'
        assert _call(connection, 'set_resource_state_all_with_guard', 'resource', 'obsolete', 'disabled')['data']['changed_count'] == 2
        connection.execute('DELETE FROM arkkan.resource_versions')
        assert _call(connection, 'set_resource_state_all', 'resource', 'enabled_default')['data']['changed_count'] == 0
        assert _call(connection, 'set_resource_state_all_with_guard', 'resource', 'disabled', 'enabled_default')['data']['changed_count'] == 0
        for name, args in (
            ('set_resource_state_all', ('missing', 'enabled')),
            ('set_resource_state_all', ('resource', None)),
            ('set_resource_state_all_with_guard', ('resource', None, 'enabled')),
            ('set_resource_state_all_with_guard', ('resource', 'disabled', 'bad')),
        ):
            assert _call(connection, name, *args)['result'] == 'error'


def test_s3_026_deletion_contracts(_initialized: None) -> None:
    with _staging_connection(_ROOT) as connection:
        _records(connection)
        for name, args in (('delete_resource', ('resource',)),
                           ('delete_resource_version', ('resource', 'opaque-version'))):
            before = _snapshot(connection)
            assert _call(connection, name, *args)['result'] == 'error'
            assert _snapshot(connection) == before
        assert _call(connection, 'delete_resource_version_all', 'resource')['data']['deleted_count'] == 0
        assert _call(connection, 'clean_up')['data'] == {'deleted_count': 0}
        for slug in ('resource', 'other'):
            for version in ('obsolete-one', 'obsolete-two'):
                assert _call(connection, 'add_resource', slug, version, 'custom')['result'] == 'success'
        connection.execute("UPDATE arkkan.resource_versions SET state = 'obsolete' WHERE version LIKE 'obsolete-%'")
        assert _call(connection, 'delete_resource_version', 'resource', 'obsolete-one')['data'] == {
            'slug': 'resource', 'version': 'obsolete-one',
        }
        assert _call(connection, 'delete_resource_version_all', 'resource')['data'] == {
            'slug': 'resource', 'deleted_count': 1,
        }
        assert _call(connection, 'clean_up')['data'] == {'deleted_count': 2}
        assert _call(connection, 'get_resource_info', 'other')['data']['versions'] == []
        assert _call(connection, 'delete_resource', 'other')['data'] == {'slug': 'other', 'deleted_version_count': 0}
        connection.execute("UPDATE arkkan.resource_versions SET state = 'obsolete'")
        assert _call(connection, 'delete_resource', 'resource')['data'] == {'slug': 'resource', 'deleted_version_count': 1}
        assert connection.execute("SELECT count(*) FROM arkkan.resource_types WHERE slug = 'custom'").fetchone() == (1,)
        for name, args in (('delete_resource', ('resource',)),
                           ('delete_resource_version_all', ('resource',)),
                           ('delete_resource_version', ('resource', 'missing')),
                           ('delete_resource', (None,)),
                           ('delete_resource_version_all', (' ',)),
                           ('delete_resource_version', ('resource', None))):
            assert _call(connection, name, *args)['result'] == 'error'


@pytest.mark.parametrize('operation,table,args', [
    ('delete_resource', 'resource_definitions', ('resource',)),
    ('clean_up', 'resource_versions', ()),
    ('set_resource_state_all', 'resource_versions', ('resource', 'enabled')),
])
def test_s3_027_mutation_failure_rolls_back(
    _initialized: None, operation: str, table: str, args: tuple[str, ...],
) -> None:
    with _staging_connection(_ROOT) as connection:
        _records(connection)
        connection.execute('UPDATE arkkan.resource_versions SET state = %s',
                           ('disabled' if operation == 'set_resource_state_all' else 'obsolete',))
        with connection.transaction(force_rollback=True):
            connection.execute("""CREATE FUNCTION pg_temp.reject_mutation() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                    RAISE EXCEPTION 'sensitive diagnostic' USING ERRCODE = '40001';
                END $$""")
            connection.execute(f"CREATE TRIGGER reject_mutation AFTER DELETE OR UPDATE ON arkkan.{table} "
                               "FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_mutation()")
            before = _snapshot(connection)
            result = _call(connection, operation, *args)
            assert result['result'] == 'error' and 'sensitive' not in result['reason']
            assert _snapshot(connection) == before

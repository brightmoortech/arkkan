"""Application database foundation tests; run only in verified staging."""

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from arkkan._db_migrations import _migration_list
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
            for table in _TABLES:
                connection.execute(sql.SQL("DROP TABLE IF EXISTS {}.{} RESTRICT").format(
                    sql.Identifier("arkkan"), sql.Identifier(table)))
                connection.execute(sql.SQL("DROP FUNCTION IF EXISTS {}.{}() RESTRICT").format(
                    sql.Identifier("arkkan"), sql.Identifier(f"reject_{table}_change")))
            for signature in (
                "api_response(text, text, jsonb, text)",
                "api_identifier_valid(text)", "api_state_valid(text)", "api_mode_valid(text)",
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
        assert result.stdout.count("[PENDING]") == 16
        assert "[APPLIED]" not in result.stdout
        with _staging_connection(_ROOT) as connection:
            assert _state(connection) == before
    result = _cli("--apply")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("[APPLIED]") == 16
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
        """).fetchone() == (0,)
        seeds = json.loads((_ROOT / "sql/migrations/012_resource_types.json").read_text())
        assert connection.execute("""
            SELECT slug, description, is_system FROM arkkan.resource_types ORDER BY slug
        """).fetchall() == [(slug, seeds[slug], True) for slug in sorted(seeds)]
    result = _cli("--apply")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("[UNCHANGED]") == 16
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
            with pytest.raises(ValueError, match="Conflicting internal API helper"):
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
        assert set(before[4]).issubset(after[4]) and len(after[4]) == len(before[4]) + 4
        assert [connection.execute(query).fetchall() for query in queries] == data_before
    assert not any(line.startswith("[APPLIED]") for line in _run(apply=True))
    with _staging_connection(_ROOT) as connection:
        assert _state(connection) == after

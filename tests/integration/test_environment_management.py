"""Real environment tests. Run only against the provisioned staging instance."""

from pathlib import Path
from uuid import uuid4

import pytest

from arkkan._provisioning import (
    _containers, _docker, _load_settings, _manage, _read_identity, _target,
)
from arkkan._test_safety import _staging_connection

_ROOT = Path(__file__).resolve().parents[2]


def test_s2_027_staging_connectivity_and_safe_rerun() -> None:
    settings = _load_settings(_ROOT)
    with _staging_connection(_ROOT, settings) as connection:
        assert _read_identity(connection) == "staging"
        identity_before = connection.execute(
            "SELECT singleton, environment_type FROM arkkan_env.environment_identity"
        ).fetchall()
        system_before = connection.execute(
            "SELECT system_identifier FROM pg_catalog.pg_control_system()"
        ).fetchone()
    before = _target(settings, _ROOT)
    assert before is not None
    _manage("check", settings, _ROOT)
    _manage("setup", settings, _ROOT)
    after = _target(settings, _ROOT)
    assert after is not None and after["Id"] == before["Id"]
    assert after["State"]["StartedAt"] == before["State"]["StartedAt"]
    with _staging_connection(_ROOT, settings) as connection:
        assert connection.execute(
            "SELECT singleton, environment_type FROM arkkan_env.environment_identity"
        ).fetchall() == identity_before
        assert connection.execute(
            "SELECT system_identifier FROM pg_catalog.pg_control_system()"
        ).fetchone() == system_before


@pytest.mark.parametrize("operation", [
    "INSERT INTO arkkan_env.environment_identity (singleton, environment_type) "
    "VALUES (TRUE, 'staging')",
    "UPDATE arkkan_env.environment_identity SET environment_type = 'development'",
    "DELETE FROM arkkan_env.environment_identity",
    "TRUNCATE TABLE arkkan_env.environment_identity",
])
def test_s2_028_identity_immutable(operation: str) -> None:
    import psycopg

    with _staging_connection(_ROOT) as connection:
        # Roll back even if the protection unexpectedly permits a mutation.
        with connection.transaction(force_rollback=True):
            with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
                connection.execute(operation)
    with _staging_connection(_ROOT) as connection:
        assert _read_identity(connection) == "staging"


def test_s2_029_ordinary_role_cannot_access_identity() -> None:
    from psycopg import sql
    from psycopg.errors import InsufficientPrivilege

    role = sql.Identifier("arkkan_test_identity_" + uuid4().hex)
    with _staging_connection(_ROOT) as connection:
        # No persistent role survives this test, including on failure.
        with connection.transaction(force_rollback=True):
            connection.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            connection.execute(sql.SQL("SET LOCAL ROLE {}").format(role))
            for statement in (
                "SELECT environment_type FROM arkkan_env.environment_identity",
                "UPDATE arkkan_env.environment_identity SET environment_type = 'production'",
                "DROP SCHEMA arkkan_env CASCADE",
            ):
                with connection.transaction(force_rollback=True):
                    with pytest.raises(InsufficientPrivilege):
                        connection.execute(statement)
    with _staging_connection(_ROOT) as connection:
        assert _read_identity(connection) == "staging"


def test_s2_030_container_recreation_preserves_storage() -> None:
    from psycopg import sql

    settings = _load_settings(_ROOT)
    name = "arkkan_test_persistence_" + uuid4().hex
    schema, role = sql.Identifier(name), sql.Identifier(name + "_role")
    created = False
    try:
        with _staging_connection(_ROOT, settings) as connection:
            with connection.transaction():
                connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
                connection.execute(sql.SQL(
                    "CREATE TABLE {}.marker (value text NOT NULL)"
                ).format(schema))
                connection.execute(sql.SQL(
                    "INSERT INTO {}.marker (value) VALUES (%s)"
                ).format(schema), (name,))
                connection.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(role))
            created = True
            system_before = connection.execute(
                "SELECT system_identifier FROM pg_catalog.pg_control_system()"
            ).fetchone()
        # Recheck staging immediately before removing exactly its container ID.
        with _staging_connection(_ROOT, settings):
            before = _target(settings, _ROOT)
            assert before is not None
        unrelated_before = {
            item["Id"]: (item["State"]["Running"], item["State"]["StartedAt"])
            for item in _containers(settings, _ROOT)
            if item["Id"] != before["Id"]
        }
        _docker(
            ["stop", "--time", "60", before["Id"]], settings, _ROOT,
            timeout=90,
        )
        _docker(["rm", before["Id"]], settings, _ROOT)
        _manage("setup", settings, _ROOT)
        after = _target(settings, _ROOT)
        assert after is not None and before["Id"] != after["Id"]
        unrelated_after = {
            item["Id"]: (item["State"]["Running"], item["State"]["StartedAt"])
            for item in _containers(settings, _ROOT)
        }
        assert all(
            unrelated_after.get(identifier) == state
            for identifier, state in unrelated_before.items()
        )
        with _staging_connection(_ROOT, settings) as connection:
            assert _read_identity(connection) == "staging"
            assert connection.execute(
                "SELECT system_identifier FROM pg_catalog.pg_control_system()"
            ).fetchone() == system_before
            marker = connection.execute(sql.SQL(
                "SELECT value FROM {}.marker"
            ).format(schema)).fetchone()
            assert marker == (name,)
            assert connection.execute(
                "SELECT rolcanlogin FROM pg_catalog.pg_roles WHERE rolname = %s",
                (name + "_role",),
            ).fetchone() == (False,)
    finally:
        if created:
            # If guard fails, stop; never bypass it to clean up test objects.
            with _staging_connection(_ROOT, settings) as connection:
                with connection.transaction():
                    connection.execute(sql.SQL("DROP TABLE {}.marker").format(schema))
                    connection.execute(sql.SQL("DROP SCHEMA {}").format(schema))
                    connection.execute(sql.SQL("DROP ROLE {}").format(role))

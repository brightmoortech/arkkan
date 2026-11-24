"""Internal Docker provisioning and environment identity operations."""

import json
import logging
import os
import re
import socket
import subprocess
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._environment import (
    _ALLOWED, _read_environment, _validate_configuration, _validate_environment,
)

if TYPE_CHECKING:
    from psycopg import Connection

_IMAGE = "postgres:18.7-bookworm"
_SERVER_VERSION = 180007
_DATA_TARGET = "/var/lib/postgresql"
_PASSWORD_TARGET = "/run/secrets/postgres_password"
_HEALTH_TEST = [
    "CMD-SHELL",
    'pg_isready -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
]
_IDENTITY_SQL = """
CREATE SCHEMA arkkan_env;
REVOKE ALL ON SCHEMA arkkan_env FROM PUBLIC;
CREATE TABLE arkkan_env.environment_identity (
    singleton boolean PRIMARY KEY DEFAULT TRUE
        CONSTRAINT valid_singleton CHECK (singleton),
    environment_type text NOT NULL CONSTRAINT valid_environment_type CHECK (
        environment_type IN ('development', 'staging', 'production')
    )
);
REVOKE ALL ON TABLE arkkan_env.environment_identity FROM PUBLIC;
"""
_IDENTITY_PROTECTION_SQL = """
CREATE FUNCTION arkkan_env.reject_identity_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE EXCEPTION 'Environment identity is immutable.';
END;
$$;
REVOKE ALL ON FUNCTION arkkan_env.reject_identity_change() FROM PUBLIC;
CREATE TRIGGER protect_environment_identity
BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE
ON arkkan_env.environment_identity
FOR EACH STATEMENT EXECUTE FUNCTION arkkan_env.reject_identity_change();
ALTER TABLE arkkan_env.environment_identity
    ENABLE ALWAYS TRIGGER protect_environment_identity;
"""


def _load_settings(root: Path, *, prepare: bool = False) -> dict[str, str]:
    raw = _read_environment(root / ".env")
    if prepare:
        settings = _validate_configuration(raw, root)
        _prepare_directories(settings, root)
        missing = [
            f"{key}: {settings[key]}" for key in (
                "POSTGRES_PASSWORD_FILE", "PGPASSFILE",
            ) if not Path(settings[key]).exists()
        ]
        if missing:
            raise ValueError(
                "Directories prepared. Operator must supply missing password "
                "files (permissions 0600), then rerun setup:\n  "
                + "\n  ".join(missing)
            )
    return _validate_environment(raw, root)


def _prepare_directories(settings: Mapping[str, str], root: Path) -> None:
    """Prepare missing directories only; never alter existing files or modes."""
    storage = Path(settings["POSTGRES_DATA_DIR"])
    directories = (
        storage, Path(settings["POSTGRES_PASSWORD_FILE"]).parent,
        Path(settings["PGPASSFILE"]).parent,
    )
    # Check all ancestors before writing so a file cannot be used as a directory.
    for directory in directories:
        for parent in (directory, *directory.parents):
            if parent.exists() and not parent.is_dir():
                raise ValueError(
                    "A configured directory or parent is not a directory."
                )
    missing = tuple(dict.fromkeys(
        directory for directory in directories if not directory.is_dir()
    ))
    if not missing:
        return
    _require_local_docker(settings, root)
    target = _target(settings, root, new_directories=missing)
    if not storage.exists():
        if target is not None:
            raise ValueError(
                "Existing container has missing storage; inspect it before proceeding."
            )
        _require_port_available(settings)
    for directory in missing:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        logging.info("Prepared directory: %s", directory)


def _client_password(settings: Mapping[str, str]) -> bytes:
    """Resolve the first matching libpq password-file entry offline."""
    try:
        contents = Path(settings["PGPASSFILE"]).read_bytes()
    except OSError:
        raise ValueError(
            "Cannot read PGPASSFILE; verify its access permissions."
        ) from None
    if b"\x00" in contents:
        raise ValueError("PGPASSFILE contains invalid data.")
    target = tuple(settings[key].encode("utf-8") for key in (
        "PGHOST", "PGPORT", "PGDATABASE", "PGUSER",
    ))
    # Match libpq's escaped fields and first-match wildcard precedence. The
    # password ends at the first unescaped colon or the end of the line.
    field = rb"((?:\\.|[^:\\])*)"
    pattern = re.compile(
        rb":".join([field] * 4) + rb":((?:\\.|[^:\\]|\\$)*)"
    )
    for line in contents.split(b"\n"):
        if line.startswith(b"#"):
            continue
        match = pattern.match(line.rstrip(b"\r"))
        if not match:
            continue
        fields = match.groups()
        if all(
            raw == b"*" or re.sub(rb"\\(.)", rb"\1", raw) == expected
            for raw, expected in zip(fields[:4], target, strict=True)
        ):
            password = re.sub(rb"\\(.)", rb"\1", fields[4])
            if password:
                return password
            break
    raise ValueError(
        "PGPASSFILE has no nonempty first matching credential; verify the entry."
    )


def _verify_initial_credentials(
    settings: Mapping[str, str], client_password: bytes,
) -> None:
    """Reject inconsistent initial passwords before creating storage."""
    try:
        password = Path(settings["POSTGRES_PASSWORD_FILE"]).read_bytes()
        password = password.removesuffix(b"\n")
    except OSError:
        raise ValueError(
            "Cannot read POSTGRES_PASSWORD_FILE; verify its access permissions."
        ) from None
    if not password or any(char in password for char in (b"\n", b"\r", b"\x00")):
        raise ValueError(
            "POSTGRES_PASSWORD_FILE must contain one nonempty password line "
            "with no carriage return or NUL."
        )
    if password != client_password:
        raise ValueError(
            "Initial provisioning and client passwords do not match; "
            "correct the credential files before setup."
        )


def _docker_environment(settings: Mapping[str, str]) -> dict[str, str]:
    # Compose interpolation must not be overridden by another checkout's settings.
    inherited = {
        key: value for key, value in os.environ.items()
        if key not in _ALLOWED and not key.startswith(("COMPOSE_", "PG"))
    }
    return {**inherited, **settings}


def _docker(
    args: list[str], settings: Mapping[str, str], root: Path,
    *, timeout: int = 30,
) -> str:
    try:
        result = subprocess.run(
            ["docker", *args], cwd=root, env=_docker_environment(settings),
            capture_output=True, text=True, check=False, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError(
            "Docker command unavailable or timed out; check Docker Desktop."
        ) from None
    if result.returncode:
        # Docker output may contain environment or credential information.
        if args[0] == "compose":
            raise ValueError(
                "PostgreSQL provisioning failed or readiness timed out; "
                "check container status, port, storage and password-file access. "
                "No recovery was attempted."
            )
        raise ValueError(
            f"Docker {args[0]} failed; check the designated infrastructure "
            "and Docker status. No recovery was attempted."
        )
    return result.stdout


def _json_output(output: str) -> Any:
    try:
        return json.loads(output)
    except (ValueError, TypeError):
        raise ValueError("Docker returned invalid inspection data.") from None


def _require_local_docker(settings: Mapping[str, str], root: Path) -> None:
    # A remote daemon would interpret bind sources on a different filesystem.
    if os.environ.get("DOCKER_HOST"):
        raise ValueError("Unset DOCKER_HOST and select a local Docker context.")
    context = _docker(["context", "show"], settings, root).strip()
    if not context:
        raise ValueError("Cannot determine the active Docker context.")
    data = _json_output(_docker(["context", "inspect", context], settings, root))
    try:
        endpoint = data[0]["Endpoints"]["docker"]["Host"]
    except (IndexError, KeyError, TypeError):
        raise ValueError("Cannot verify the Docker context endpoint.") from None
    if not isinstance(endpoint, str) or not endpoint.startswith("unix:///"):
        raise ValueError("Provisioning requires a local Unix-socket Docker daemon.")


def _containers(settings: Mapping[str, str], root: Path) -> list[dict[str, Any]]:
    identifiers = _docker(["ps", "-aq", "--no-trunc"], settings, root).split()
    if not identifiers:
        return []
    data = _json_output(_docker(["inspect", *identifiers], settings, root))
    if not isinstance(data, list) or len(data) != len(identifiers):
        raise ValueError("Cannot verify existing Docker containers.")
    return data


def _container_matches(
    container: Mapping[str, Any], settings: Mapping[str, str],
) -> None:
    try:
        config = container["Config"]
        labels = config.get("Labels") or {}
        bindings = container["HostConfig"]["PortBindings"]
        mounts = container["Mounts"]
        env = dict(item.split("=", 1) for item in config["Env"])
        expected_env = {
            "POSTGRES_DB": settings["PGDATABASE"],
            "POSTGRES_USER": settings["PGUSER"],
            "POSTGRES_PASSWORD_FILE": _PASSWORD_TARGET,
            "POSTGRES_INITDB_ARGS": "--auth-host=scram-sha-256",
            "PGDATA": "/var/lib/postgresql/18/docker",
        }
        expected_mounts = {
            _DATA_TARGET: (settings["POSTGRES_DATA_DIR"], True),
            _PASSWORD_TARGET: (settings["POSTGRES_PASSWORD_FILE"], False),
        }
        actual_mounts = {
            item["Destination"]: (str(Path(item["Source"]).resolve()), item["RW"])
            for item in mounts if item["Type"] == "bind"
        }
        expected_bindings = {"5432/tcp": [
            {"HostIp": "127.0.0.1", "HostPort": settings["PGPORT"]},
        ]}
        matches = (
            container["Name"] == "/" + settings["POSTGRES_CONTAINER_NAME"]
            and labels.get("com.docker.compose.project")
            == settings["COMPOSE_PROJECT_NAME"]
            and labels.get("com.docker.compose.service") == "postgres"
            and config["Image"] == _IMAGE
            and config.get("Healthcheck", {}).get("Test") == _HEALTH_TEST
            and bindings == expected_bindings
            and len(mounts) == 2 and actual_mounts == expected_mounts
            and all(env.get(key) == value for key, value in expected_env.items())
            and "POSTGRES_PASSWORD" not in env
        )
    except (KeyError, TypeError, ValueError, OSError, RuntimeError):
        matches = False
    if not matches:
        raise ValueError(
            "Existing PostgreSQL container conflicts with configuration; "
            "inspect it without replacing it."
        )


def _overlaps(first: Path, second: Path) -> bool:
    return first.is_relative_to(second) or second.is_relative_to(first)


def _target(
    settings: Mapping[str, str], root: Path,
    *, new_directories: tuple[Path, ...] = (),
) -> dict[str, Any] | None:
    target = None
    storage = Path(settings["POSTGRES_DATA_DIR"])
    for container in _containers(settings, root):
        try:
            name = container["Name"]
            labels = container["Config"].get("Labels") or {}
            if name == "/" + settings["POSTGRES_CONTAINER_NAME"]:
                _container_matches(container, settings)
                target = container
                continue
            if labels.get("com.docker.compose.project") == settings[
                "COMPOSE_PROJECT_NAME"
            ]:
                raise ValueError(
                    "The designated Compose project contains an unexpected container."
                )
            for mount in container["Mounts"]:
                if mount["Type"] != "bind":
                    continue
                source = Path(mount["Source"]).resolve()
                if _overlaps(storage, source):
                    raise ValueError(
                        "PostgreSQL storage overlaps an unrelated container's bind mount."
                    )
                if any(_overlaps(path, source) for path in new_directories):
                    raise ValueError(
                        "Directory preparation overlaps an unrelated container's "
                        "bind mount."
                    )
            bindings = container["HostConfig"].get("PortBindings") or {}
            if any(
                binding.get("HostPort") == settings["PGPORT"]
                for port, endpoint in bindings.items() if port.endswith("/tcp")
                for binding in (endpoint or [])
            ):
                raise ValueError(
                    "Configured PostgreSQL port conflicts with another container."
                )
        except (KeyError, TypeError, OSError, RuntimeError):
            raise ValueError("Cannot safely inspect existing container mounts.") from None
    return target


def _require_port_available(settings: Mapping[str, str]) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", int(settings["PGPORT"])))
    except OSError:
        raise ValueError("Configured PostgreSQL host port is unavailable.") from None


def _compose_up(settings: Mapping[str, str], root: Path) -> None:
    _docker([
        "compose", "--project-directory", str(root), "--env-file", os.devnull,
        "--project-name", settings["COMPOSE_PROJECT_NAME"], "-f",
        str(root / "compose.yaml"), "up", "-d", "--no-recreate", "--wait",
        "--wait-timeout", "120", "postgres",
    ], settings, root, timeout=180)


def _require_ready(container: dict[str, Any] | None) -> dict[str, Any]:
    if not container or not container.get("State", {}).get("Running"):
        raise ValueError("Designated PostgreSQL container is not running; run setup.")
    if container["State"].get("Health", {}).get("Status") != "healthy":
        raise ValueError("Designated PostgreSQL container is not healthy; inspect its status.")
    ports = container.get("NetworkSettings", {}).get("Ports")
    if ports != container["HostConfig"]["PortBindings"]:
        raise ValueError("Running container port mapping does not match configuration.")
    return container


def _require_client_environment() -> None:
    # libpq can otherwise use implicit services, passwords or target overrides.
    if any(key.startswith("PG") and key not in _ALLOWED for key in os.environ):
        raise ValueError("Unset additional PG environment variables before provisioning or testing.")


@contextmanager
def _connect(settings: Mapping[str, str]) -> Iterator["Connection[Any]"]:
    import psycopg

    _require_client_environment()
    try:
        with psycopg.connect(
            host=settings["PGHOST"], hostaddr="127.0.0.1",
            port=settings["PGPORT"], dbname=settings["PGDATABASE"],
            user=settings["PGUSER"], passfile=settings["PGPASSFILE"],
            require_auth="scram-sha-256", connect_timeout=5,
            autocommit=True,
        ) as connection:
            yield connection
    except psycopg.Error:
        raise ValueError(
            "PostgreSQL connection or operation failed; verify readiness, "
            "password-file authentication, privileges and database state."
        ) from None


def _verify_database(
    connection: "Connection[Any]", settings: Mapping[str, str],
    container: Mapping[str, Any],
) -> None:
    result = connection.execute("""
        SELECT pg_catalog.current_database(), CURRENT_USER,
               pg_catalog.inet_server_port(),
               pg_catalog.current_setting('server_version_num')::integer,
               (SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = CURRENT_USER),
               pg_catalog.host(pg_catalog.inet_server_addr())
    """).fetchone()
    addresses = {
        network.get("IPAddress")
        for network in container.get("NetworkSettings", {}).get("Networks", {}).values()
        if network.get("IPAddress")
    }
    if (
        not result or result[:5] != (
            settings["PGDATABASE"], settings["PGUSER"], 5432, _SERVER_VERSION, True,
        ) or result[5] not in addresses
    ):
        raise ValueError(
            "Connected database, container address, role privileges or "
            "PostgreSQL version do not match configuration."
        )


def _read_identity(connection: "Connection[Any]") -> str:
    relation = connection.execute("""
        SELECT c.relkind,
               pg_catalog.pg_get_userbyid(c.relowner) = CURRENT_USER,
               pg_catalog.pg_get_userbyid(n.nspowner) = CURRENT_USER,
               NOT EXISTS (
                   SELECT 1 FROM pg_catalog.aclexplode(COALESCE(
                       c.relacl, pg_catalog.acldefault('r', c.relowner)
                   )) AS acl WHERE acl.grantee <> c.relowner
               ),
               NOT EXISTS (
                   SELECT 1 FROM pg_catalog.aclexplode(COALESCE(
                       n.nspacl, pg_catalog.acldefault('n', n.nspowner)
                   )) AS acl WHERE acl.grantee <> n.nspowner
               ),
               EXISTS (
                   SELECT 1 FROM pg_catalog.pg_trigger AS t
                   JOIN pg_catalog.pg_proc AS p ON p.oid = t.tgfoid
                   WHERE t.tgrelid = c.oid AND NOT t.tgisinternal
                     AND t.tgname = 'protect_environment_identity'
                     AND t.tgenabled = 'A' AND t.tgtype = 62
                     AND p.pronamespace = n.oid
                     AND p.proname = 'reject_identity_change'
               ),
               (SELECT count(*) FROM pg_catalog.pg_constraint AS con
                WHERE con.conrelid = c.oid AND con.convalidated
                  AND (con.contype = 'p' OR
                       (con.contype = 'c' AND con.conname IN
                           ('valid_singleton', 'valid_environment_type')))) = 3
        FROM pg_catalog.pg_class AS c
        JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'arkkan_env' AND c.relname = 'environment_identity'
    """).fetchone()
    if relation != ("r", True, True, True, True, True, True):
        raise ValueError("Environment identity is missing or invalid; do not recreate it automatically.")
    rows = connection.execute("""
        SELECT singleton, environment_type
        FROM arkkan_env.environment_identity
    """).fetchall()
    if len(rows) != 1 or rows[0][0] is not True or rows[0][1] not in (
        "development", "staging", "production",
    ):
        raise ValueError("Environment identity is missing or invalid.")
    return rows[0][1]


def _verify_identity(connection: "Connection[Any]", expected: str) -> None:
    if _read_identity(connection) != expected:
        raise ValueError("Stored environment identity does not match configuration; aborting.")


def _create_identity(connection: "Connection[Any]", expected: str) -> None:
    # Only the first successful provisioning of previously empty storage may create it.
    with connection.transaction():
        connection.execute(_IDENTITY_SQL)
        connection.execute("""
            INSERT INTO arkkan_env.environment_identity (singleton, environment_type)
            VALUES (TRUE, %s)
        """, (expected,))
        connection.execute(_IDENTITY_PROTECTION_SQL)
        _verify_identity(connection, expected)


def _manage(command: str, settings: Mapping[str, str], root: Path) -> None:
    if command not in ("setup", "check"):
        raise ValueError("Unsupported environment management command.")
    _require_client_environment()
    import_module("psycopg")
    client_password = _client_password(settings)
    _require_local_docker(settings, root)
    target = _target(settings, root)
    storage = Path(settings["POSTGRES_DATA_DIR"])
    fresh = False
    running = target is not None and target.get("State", {}).get("Running")
    if command == "setup" and not running:
        empty = not storage.exists() or not any(storage.iterdir())
        fresh = target is None and empty
        if not empty and not (storage / "18" / "docker" / "PG_VERSION").is_file():
            raise ValueError(
                "Nonempty storage does not contain a readable PostgreSQL cluster marker."
            )
        if target is not None and empty:
            raise ValueError(
                "Existing container has missing or empty storage; inspect it before proceeding."
            )
        if fresh:
            _verify_initial_credentials(settings, client_password)
        _require_port_available(settings)
        if not storage.exists():
            storage.mkdir(parents=True, exist_ok=False)
        _compose_up(settings, root)
        target = _target(settings, root)
    target = _require_ready(target)
    with _connect(settings) as connection:
        _verify_database(connection, settings, target)
        if command == "setup" and fresh:
            _create_identity(connection, settings["ARKKAN_ENVIRONMENT"])
        else:
            with connection.transaction():
                connection.execute("SET TRANSACTION READ ONLY")
                _verify_identity(connection, settings["ARKKAN_ENVIRONMENT"])

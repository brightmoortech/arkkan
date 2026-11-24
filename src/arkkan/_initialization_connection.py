"""Connection and prerequisite checks for the reusable initialization workflow."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg import Connection


@contextmanager
def _initialization_connection(
    settings: Mapping[str, str], *, required_major: int,
    password_file: Path, local_scram: bool = False,
) -> Iterator["Connection[Any]"]:
    """Open an idle privileged connection without provisioning a database."""
    import psycopg

    database = settings.get("PGDATABASE", "")
    user = settings.get("PGUSER", "")
    if not database.strip() or not user.strip():
        raise ValueError("PGDATABASE and PGUSER are required.")
    port = settings.get("PGPORT") or "5432"
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("PGPORT must be an integer from 1 to 65535.")
    options: dict[str, Any] = {
        "dbname": database, "user": user, "port": port,
        "passfile": str(password_file), "connect_timeout": 5,
        "autocommit": True,
    }
    if settings.get("PGHOST"):
        options["host"] = settings["PGHOST"]
    if local_scram:
        if settings.get("PGHOST") not in ("localhost", "127.0.0.1"):
            raise ValueError("Local provisioning requires the IPv4 loopback host.")
        options.update(hostaddr="127.0.0.1", require_auth="scram-sha-256")
    with psycopg.connect(**options) as connection:
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL search_path = pg_catalog")
            result = connection.execute("""
                SELECT pg_catalog.current_database(), CURRENT_USER,
                       pg_catalog.current_setting('server_version_num')::integer,
                       (SELECT rolsuper FROM pg_catalog.pg_roles
                        WHERE rolname = CURRENT_USER),
                       pg_catalog.pg_is_in_recovery()
            """).fetchone()
            if result is None or result[:2] != (database, user):
                raise ValueError("Connected database or role does not match configuration.")
            if result[2] // 10000 != required_major:
                raise ValueError(f"Initialization requires PostgreSQL {required_major}.")
            if not result[3]:
                raise ValueError("Initialization requires the deployment PostgreSQL superuser.")
            if result[4]:
                raise ValueError("Initialization requires a writable primary PostgreSQL server.")
        yield connection

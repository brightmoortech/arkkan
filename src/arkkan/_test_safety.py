"""Fail-closed safety guard shared by automated PostgreSQL tests."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._provisioning import (
    _connect, _load_settings, _require_local_docker, _require_ready,
    _target, _verify_database, _verify_identity,
)

if TYPE_CHECKING:
    from psycopg import Connection


@contextmanager
def _staging_connection(
    root: Path, settings: Mapping[str, str] | None = None,
) -> Iterator["Connection[Any]"]:
    # Use validated local configuration and independently verify the database.
    configured = _load_settings(root)
    if settings is not None and dict(settings) != configured:
        raise ValueError("Requested test target differs from the local configuration.")
    if configured["ARKKAN_ENVIRONMENT"] != "staging":
        raise ValueError("Database tests require the designated staging environment.")
    _require_local_docker(configured, root)
    target = _require_ready(_target(configured, root))
    with _connect(configured) as connection:
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            _verify_database(connection, configured, target)
            _verify_identity(connection, "staging")
        yield connection

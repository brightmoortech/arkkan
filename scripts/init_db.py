#!/usr/bin/env python3
"""Inspect or initialize the existing application database (Stage 3 PostgreSQL API)."""

import argparse
import logging
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from arkkan._config import _connection_settings
from arkkan._db_migrations import _migration_list
from arkkan._environment import _credential_file, _read_environment
from arkkan._initialization_connection import _initialization_connection
from arkkan._migration_workflow import _run_migrations
from arkkan._provisioning import _verify_identity

_ROOT = Path(__file__).resolve().parents[1]
_PG_KEYS = frozenset(("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSFILE"))
# Stable, project-specific identifier for cooperating initialization sessions.
_LOCK_KEY = int.from_bytes(b"arkkanDB", "big", signed=True)


def _settings(
    root: Path, environ: Mapping[str, str],
) -> tuple[dict[str, str], Path, str | None]:
    if any(key.startswith("PG") and key not in _PG_KEYS for key in environ):
        raise ValueError("Unset additional PG environment variables before initialization.")
    local = root / ".env"
    if local.exists() or local.is_symlink():
        values = _read_environment(local)
        source = {key: value for key, value in values.items() if key in _PG_KEYS}
        # Do not allow implicit overrides to target another database.
        if any(source.get(key) != value for key, value in environ.items() if key in _PG_KEYS):
            raise ValueError("PG environment settings conflict with the local .env configuration.")
        identity = values.get("ARKKAN_ENVIRONMENT")
        if identity not in ("development", "staging", "production"):
            raise ValueError("Invalid or missing ARKKAN_ENVIRONMENT in local .env.")
    else:
        source = dict(environ)
        identity = None
    settings = _connection_settings(source)
    if identity in ("development", "staging") and (
        not settings.get("PGHOST") or not settings.get("PGPORT")
    ):
        raise ValueError("Local initialization requires explicit PGHOST and PGPORT.")
    if settings["PGUSER"] in ("arkkan_admin", "arkkan_user"):
        raise ValueError("Use the deployment superuser, not an application API role.")
    if settings["PGDATABASE"] in ("postgres", "template0", "template1"):
        raise ValueError("Select the dedicated application database, not a maintenance database.")
    passfile = _credential_file(
        settings.get("PGPASSFILE") or "~/.pgpass", root, "PGPASSFILE",
    )
    return settings, passfile, identity


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Dry run (default); no database writes.")
    mode.add_argument("--apply", action="store_true", help="Apply pending verified migration steps.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    try:
        import psycopg
    except ImportError:
        logging.error("PostgreSQL driver unavailable; run the project bootstrap.")
        return 1
    try:
        settings, passfile, identity = _settings(_ROOT, os.environ)
        migrations = _migration_list(_ROOT)
        with _initialization_connection(
            settings, required_major=18, password_file=passfile,
            local_scram=identity is not None and identity != "production",
        ) as connection:
            if identity is not None:
                with connection.transaction():
                    connection.execute("SET TRANSACTION READ ONLY")
                    connection.execute("SET LOCAL search_path = pg_catalog")
                    _verify_identity(connection, identity)
            print(f"[INFO] Database: {settings['PGDATABASE']}; "
                  f"role: {settings['PGUSER']}; mode: {'apply' if args.apply else 'dry run'}.", flush=True)
            print("[INFO] Stage 3 PostgreSQL API; verifying all functions and role grants.", flush=True)
            _run_migrations(connection, migrations, apply=args.apply, lock_key=_LOCK_KEY,
                            report=lambda message: print(message, flush=True))
    except ValueError as error:
        logging.error("%s", error)
        return 1
    except (OSError, UnicodeError):
        logging.error("Cannot read initialization inputs; verify paths, permissions and encoding.")
        return 1
    except psycopg.Error as error:
        logging.error("PostgreSQL operation failed (SQLSTATE %s); verify connectivity, privileges and migration state.",
                      error.sqlstate or "unknown")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

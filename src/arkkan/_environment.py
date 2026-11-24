"""Internal contract for local PostgreSQL environment provisioning."""

import os
import re
import stat
from collections.abc import Mapping
from pathlib import Path

_REQUIRED = (
    "ARKKAN_ENVIRONMENT", "COMPOSE_PROJECT_NAME", "POSTGRES_CONTAINER_NAME",
    "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "POSTGRES_DATA_DIR",
    "POSTGRES_PASSWORD_FILE",
)
_ALLOWED = frozenset((*_REQUIRED, "PGPASSFILE"))
_IDENTITIES = frozenset(("development", "staging", "production"))


def _is_literal(value: str) -> bool:
    return (
        value == value.strip()
        and not any(char in value for char in "\"'`$\\#")
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


def _read_environment(path: Path) -> dict[str, str]:
    """Read literal dotenv assignments without executing shell code."""
    settings: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise ValueError("Cannot read the local .env configuration.") from None
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if (
            not separator or key not in _ALLOWED or key in settings
            or not _is_literal(value)
        ):
            raise ValueError(
                f"Invalid or duplicate .env assignment on line {number}."
            )
        settings[key] = value
    return settings


def _resolved_path(value: str, root: Path) -> Path:
    try:
        return (root / Path(value).expanduser()).resolve()
    except (OSError, RuntimeError, ValueError):
        raise ValueError("Cannot resolve a configured path.") from None


def _credential_file(value: str, root: Path, variable: str) -> Path:
    path = _resolved_path(value, root)
    try:
        info = path.stat()
    except OSError:
        raise ValueError(
            f"{variable} must identify an existing password file."
        ) from None
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(
            f"{variable} must be a regular file with permissions 0600."
        )
    if not os.access(path, os.R_OK):
        raise ValueError(f"{variable} must be readable by the operator.")
    if not info.st_size:
        raise ValueError(f"{variable} must not identify an empty password file.")
    if path.is_relative_to(root.resolve()) or any(
        (parent / ".git").exists() for parent in path.parents
    ):
        raise ValueError(
            f"{variable} must be outside repository checkouts."
        )
    return path


def _validate_configuration(
    settings: Mapping[str, str], root: Path,
) -> dict[str, str]:
    """Validate and resolve configuration without requiring credential files."""
    if set(settings) - _ALLOWED:
        raise ValueError("Unsupported environment configuration key.")
    if not all(_is_literal(value) for value in settings.values()):
        raise ValueError("Invalid literal environment configuration value.")
    for key in _REQUIRED:
        if not settings.get(key, "").strip():
            raise ValueError(f"{key} is required and must not be blank.")
    if settings["ARKKAN_ENVIRONMENT"] not in _IDENTITIES:
        raise ValueError(
            "ARKKAN_ENVIRONMENT must be development, staging or production."
        )
    if not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]*", settings["COMPOSE_PROJECT_NAME"]
    ):
        raise ValueError(
            "COMPOSE_PROJECT_NAME is not a valid Compose project name."
        )
    if not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", settings["POSTGRES_CONTAINER_NAME"]
    ):
        raise ValueError(
            "POSTGRES_CONTAINER_NAME is not a valid container name."
        )
    if settings["PGHOST"] not in ("localhost", "127.0.0.1"):
        raise ValueError(
            "PGHOST must identify the local IPv4 loopback interface."
        )
    port = settings["PGPORT"]
    if not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535:
        raise ValueError("PGPORT must be an integer from 1 to 65535.")
    if settings["PGUSER"] in ("arkkan_admin", "arkkan_user"):
        raise ValueError("PGUSER must identify the provisioning superuser.")
    if settings["PGDATABASE"] in ("template0", "template1", "postgres"):
        raise ValueError(
            "PGDATABASE must identify a dedicated application database."
        )
    data_dir = _resolved_path(settings["POSTGRES_DATA_DIR"], root)
    checkout = root.resolve()
    if data_dir == data_dir.parent or checkout.is_relative_to(data_dir):
        raise ValueError(
            "POSTGRES_DATA_DIR must not contain the repository checkout."
        )
    if settings["ARKKAN_ENVIRONMENT"] != "production" and (
        data_dir.is_relative_to(checkout)
        or any(
            (parent / ".git").exists()
            for parent in (data_dir, *data_dir.parents)
        )
    ):
        raise ValueError(
            "POSTGRES_DATA_DIR must be outside repository checkouts."
        )
    if data_dir.exists() and not data_dir.is_dir():
        raise ValueError("POSTGRES_DATA_DIR must identify a directory.")
    password_file = _resolved_path(settings["POSTGRES_PASSWORD_FILE"], root)
    passfile = _resolved_path(settings.get("PGPASSFILE") or "~/.pgpass", root)
    for variable, path in (
        ("POSTGRES_PASSWORD_FILE", password_file), ("PGPASSFILE", passfile),
    ):
        if path.is_relative_to(checkout) or any(
            (parent / ".git").exists() for parent in path.parents
        ):
            raise ValueError(f"{variable} must be outside repository checkouts.")
        if path.is_relative_to(data_dir) or data_dir.is_relative_to(path):
            raise ValueError(
                "Password files must be outside PostgreSQL data storage."
            )
        if path.exists() and not path.is_file():
            raise ValueError(f"{variable} must identify a regular password file.")
    if (
        password_file.is_relative_to(passfile)
        or passfile.is_relative_to(password_file)
    ):
        raise ValueError("Provisioning and client password files must be separate.")
    return {
        **settings,
        "PGPORT": str(int(port)),
        "POSTGRES_DATA_DIR": str(data_dir),
        "POSTGRES_PASSWORD_FILE": str(password_file),
        "PGPASSFILE": str(passfile),
    }


def _validate_environment(
    settings: Mapping[str, str], root: Path,
) -> dict[str, str]:
    """Validate configuration and required credential files without writes."""
    resolved = _validate_configuration(settings, root)
    password_file = _credential_file(
        resolved["POSTGRES_PASSWORD_FILE"], root, "POSTGRES_PASSWORD_FILE"
    )
    passfile = _credential_file(resolved["PGPASSFILE"], root, "PGPASSFILE")
    if password_file.samefile(passfile):
        raise ValueError("Provisioning and client password files must be separate.")
    return resolved

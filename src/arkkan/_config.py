"""Internal validation of PostgreSQL connection settings."""

import os
from collections.abc import Mapping


def _connection_settings(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Validate required settings without connecting or reading credentials."""
    source = os.environ if environ is None else environ
    settings: dict[str, str] = {}
    for variable in ("PGDATABASE", "PGUSER"):
        value = source.get(variable)
        if value is None or not value.strip():
            raise ValueError(f"{variable} is required and must not be blank.")
        settings[variable] = value

    # Leave optional connection defaults and syntax to libpq.
    for variable in ("PGHOST", "PGPORT", "PGPASSFILE"):
        if variable in source:
            settings[variable] = source[variable]
    return settings

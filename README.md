# arkkan

A centralized repository for versioned prompt resources. See the Functional
and Technical Requirements in `arkkan.wiki/` for the project scope.

## Development setup

Use Python 3.12.10 on macOS for Phase 1. From the project root, run:

```bash
./scripts/bootstrap.sh
```

The bootstrap script creates or reuses `.venv`, verifies its Python version,
installs pinned dependencies, installs the package in editable mode, checks
installed dependency compatibility, and runs the automated tests. Recreate
virtual environments locally rather than copying them between machines.

Python is pinned in `.python-version` and `pyproject.toml`. Installation tools
are pinned in `requirements-bootstrap.txt`; test dependencies are pinned in
`requirements.txt`. No third-party runtime dependencies are required by the
project foundation. These pins identify package versions; they do not guarantee
an offline or byte-identical build.

## Configuration

`.env.example` documents the standard PostgreSQL environment variables used by
later stages. It is not loaded automatically. Set `PGDATABASE` and `PGUSER` in
the process environment when database access is required. Optional `PGHOST`,
`PGPORT`, and `PGPASSFILE` values are passed through unchanged; libpq supplies
its defaults when omitted. Do not put passwords in project files.

Stage 1 validates the required settings without connecting to PostgreSQL.
Database initialization, authentication and resource operations are not part of
Stage 1. No PostgreSQL installation or credentials are needed to run these tests.

## Automated tests

After bootstrap, run from the project root:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/unit
```

Integration and end-to-end suites are reserved for later implementation stages.
See `arkkan.wiki/TESTING.md` for testing governance and
`arkkan.wiki/TEST_SPECIFICATION.md` for test cases and requirements traceability.

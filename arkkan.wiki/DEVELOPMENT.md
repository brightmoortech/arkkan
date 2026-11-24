# arkkan Development Guide

This guide is for contributors and maintainers of `arkkan`. For the project
purpose and user-facing documentation, see [README.md](../README.md).

## Development Setup

Use Python 3.12.10 on macOS for Phase 1. From the repository root, run:

```bash
./scripts/bootstrap.sh
```

The bootstrap script creates or reuses `.venv`, verifies its Python version,
installs pinned dependencies, installs the package in editable mode, checks
installed dependency compatibility, and runs the automated tests. Recreate
virtual environments locally rather than copying them between machines.

Python is pinned in `.python-version` and `pyproject.toml`. Installation tools
are pinned in `requirements-bootstrap.txt`, runtime dependencies in
`requirements-runtime.txt`, and test dependencies in `requirements.txt`.
The PostgreSQL driver uses Psycopg 3 with the binary distribution.
These pins identify package versions; they do not guarantee
an offline or byte-identical build.

## Configuration

[`.env.example`](../.env.example) is the shared configuration template. Each
checkout has its own ignored `.env` file. For local provisioning, use literal
`KEY=VALUE` assignments with full-line comments; do not use shell commands,
quotes, interpolation or inline comments. Provisioning requires explicit
connection and infrastructure settings. Paths can be absolute, checkout-relative
or start with `~/`; the provisioning configuration validator resolves them.
Keep both password files outside the checkout, separate from one another and
from PostgreSQL data, with file permissions `0600`. Never store password values
in `.env`.

The shared [Compose definition](../compose.yaml) pins PostgreSQL 18.7 and binds
external persistent storage to `/var/lib/postgresql`. Development and staging
use independent Compose projects, containers and data directories as specified
in Technical Requirements, under Environment Architecture and Data Architecture.
The environment management utility and database initialization are not yet
implemented in this work package. Do not start the database manually using the
new Compose definition; provisioning will be verified through the environment
management utility once available.

For ordinary application connections, the configuration code uses standard
libpq process environment variables. `PGDATABASE` and `PGUSER` are required;
optional values follow libpq defaults when omitted. The application does not
load `.env` automatically. The provisioning validator does not open a database
connection or alter any files.

## Automated Tests

After bootstrap, run from the repository root:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/unit
```

The first command runs all collected tests; the second runs only unit tests.
The current unit suite also verifies that the pinned Psycopg binary driver
imports. It does not require Docker, a database connection or actual password
files. Database integration and end-to-end tests will be introduced within
their authorized implementation scope.

## Project Documentation

- [Functional Requirements](FUNCTIONAL_REQ.md)
- [Technical Requirements](TECHNICAL_REQ.md)
- [Coding Conventions](CODING_CONVENTIONS.md)
- [Testing Governance](TESTING.md)
- [Test Specification](TEST_SPECIFICATION.md)

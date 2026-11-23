# arkkan Development Guide

This guide is for contributors and maintainers of `arkkan`. For the project
purpose and user-facing documentation, see [README.md](README.md).

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
are pinned in `requirements-bootstrap.txt`; test dependencies are pinned in
`requirements.txt`. No third-party runtime dependencies are required by the
project foundation. These pins identify package versions; they do not guarantee
an offline or byte-identical build.

## Configuration

[`.env.example`](.env.example) documents the standard PostgreSQL environment
variables used by later stages. It is not loaded automatically. Set `PGDATABASE`
and `PGUSER` in the process environment when database access is required.
Optional `PGHOST`, `PGPORT`, and `PGPASSFILE` values are passed through unchanged
by the Stage 1 configuration code; libpq supplies defaults when omitted in
subsequent database access implementations. Do not put passwords in project
files.

Stage 1 validates required settings without connecting to PostgreSQL. Database
initialization, authentication, and resource operations are not implemented.
No PostgreSQL installation or credentials are needed to run Stage 1 tests.

## Automated Tests

After bootstrap, run from the repository root:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/unit
```

The first command runs all collected tests; the second runs only unit tests.
Integration and end-to-end suites are reserved for later implementation stages.

## Project Documentation

- [Functional Requirements](arkkan.wiki/FUNCTIONAL_REQ.md)
- [Technical Requirements](arkkan.wiki/TECHNICAL_REQ.md)
- [Coding Conventions](arkkan.wiki/CODING_CONVENTIONS.md)
- [Testing Governance](arkkan.wiki/TESTING.md)
- [Test Specification](arkkan.wiki/TEST_SPECIFICATION.md)

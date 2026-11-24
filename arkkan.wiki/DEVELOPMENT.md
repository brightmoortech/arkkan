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
installed dependency compatibility, and runs the unit tests. Recreate
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

The shared [Compose definition](../compose.yaml) pins PostgreSQL 18.7 and binds
external persistent storage to `/var/lib/postgresql`. Development and staging
use independent Compose projects, containers and data directories as specified
in Technical Requirements, under Environment Architecture and Data Architecture.
Provision each PostgreSQL instance through the environment management utility
below. Application database initialization is a separate operation and is not
yet implemented.

For ordinary application connections, the configuration code uses standard
libpq process environment variables. `PGDATABASE` and `PGUSER` are required;
optional values follow libpq defaults when omitted. The application does not
load `.env` automatically. The provisioning validator does not open a database
connection or alter any files.

## PostgreSQL Environment Provisioning

### Local configuration and credentials

Use the development checkout for changes and a separate staging checkout of a
committed revision for validation. Bootstrap each checkout independently. Copy
`.env.example` to `.env` if `.env` does not already exist, then supply values
for that environment. The environment architecture is defined in Technical Requirements. The local
ports were changed from the original proposals to avoid conflicts with
existing infrastructure.
The following non-secret values describe the validated local configuration;
ports and paths remain configurable, not application defaults.

| Setting | Development | Staging |
|---|---|---|
| `ARKKAN_ENVIRONMENT` | `development` | `staging` |
| `COMPOSE_PROJECT_NAME` | `arkkan_develop` | `arkkan_stage` |
| `POSTGRES_CONTAINER_NAME` | `arkkan-db-dev` | `arkkan-db-test` |
| `PGHOST` | `localhost` | `localhost` |
| `PGPORT` | `5441` | `5442` |
| `PGDATABASE` | `arkkan_dev` | `arkkan_test` |
| `PGUSER` | `postgres` | `postgres` |
| `PGPASSFILE` | `~/.pgpass` | `~/.pgpass` |
| `POSTGRES_DATA_DIR` | `~/development/data/arkkan/develop/postgres` | `~/development/data/arkkan/stage/postgres` |
| `POSTGRES_PASSWORD_FILE` | `~/development/data/arkkan/develop/secrets/postgres_password` | `~/development/data/arkkan/stage/secrets/postgres_password` |

Adjust the workspace root, ports, and credential paths for other machines.
Choose the initial PostgreSQL superuser name through `PGUSER`; it is not fixed
by `arkkan`. Stopped Docker containers retain their configured port mappings. The utility
treats those mappings as conflicts even if no process is listening. Do not
remove or reconfigure unrelated infrastructure to resolve a conflict.

The operator supplies two separate credential files outside the repository
checkout and PostgreSQL storage, each with permissions `0600`. Use a single-line password
(with Unix line endings if a newline is present) in the provisioning file and
the corresponding libpq entry in the client password file (`PGPASSFILE`, or
`~/.pgpass` by default). Reuse existing valid credential files; the utility
never creates, changes or synchronizes credentials.

The client password file uses the following format:

```text
host:port:database:user:password
```

Replace the field names with the actual connection values and password. The
local development and staging entries have the following form (replace each
placeholder with its corresponding provisioning password):

```text
localhost:5441:arkkan_dev:postgres:<development_password>
localhost:5442:arkkan_test:postgres:<staging_password>
```

Preserve unrelated entries; the first matching client password-file entry
is used, including wildcard entries. Escape literal colons and backslashes
in password-file fields with a backslash. Set both credential files to
permissions `0600` using `chmod 600` on the respective files. Do not put passwords in `.env`, shell commands, or Git.
On initial provisioning, the passwords must match for each environment.
Changing the provisioning file does not change a stored database password.

Set `POSTGRES_DATA_DIR` to the approved external storage location for the
selected environment, not a directory inside the checkout. Use the designated
Compose project, container, port, database and environment identity in `.env`.
The provisioning utility reads the local file directly without sourcing it as
shell code. Do not set additional libpq environment variables such as
`PGPASSWORD` or `PGSERVICE` for these operations. Select a local Docker context;
remote Docker endpoints are not supported by this local provisioning utility.

### Provision and verify

With Docker Desktop running, execute from the configured checkout after
supplying `.env`, even if the credential files do not yet exist:

```bash
.venv/bin/python scripts/manage_environment.py setup
```

The `setup` command validates paths and checks for infrastructure conflicts
before creating missing PostgreSQL storage and credential-parent directories. Existing
valid directories are reused without changing their permissions. If credentials
are missing, `setup` reports the required file paths and permissions and stops
without starting a container or initializing a database. The current utility
labels this expected first-time prerequisite as `[ERROR]`. Supply the missing
provisioning password file and ensure the matching client password-file entry
is present as described above, even if that client file already exists. Then
rerun `setup`. No manual directory or container creation is required.

Before starting PostgreSQL, `setup` checks the driver and client password-file
entry. For a new database, it verifies that the initial passwords match before
starting the container. It creates or starts the designated container as needed
and verifies password-file SCRAM authentication.

`setup` establishes the immutable environment identity only when provisioning
new empty storage. For an existing cluster, it verifies the stored identity and
uses the current client credential without requiring it to match the original
provisioning password. After `setup` succeeds, verify the environment:

```bash
.venv/bin/python scripts/manage_environment.py check
```

The `check` command verifies the running instance and stored identity without
provisioning or modifying data. Both commands can be rerun against a valid
environment. Neither command deletes containers, persistent storage or
credentials, or modifies credential file permissions.

If provisioning fails, inspect the reported error before taking further action.
An existing cluster with a missing or mismatched identity is rejected, including
when a first provisioning attempt created storage but did not establish the
identity. Do not delete storage or relabel an existing database to bypass this
check. The utility does not perform recovery or password rotation.

### Staging validation

Prepare the staging checkout at the committed development revision. For an
existing clean staging checkout, run `git fetch origin` followed by
`git switch --detach <commit>` (replace `<commit>` with the revision selected
for validation). Confirm the revision and clean working tree using
`git log -1 --oneline` and `git status --short --branch`. Do not use `git pull`
to advance a pinned staging revision. Bootstrap independently, supply its own
`.env`, follow the same `setup` and credential provisioning sequence, then
run `check` before the database test suite. Do not modify source files in
staging.

## Automated Tests

Run unit tests in development or staging without starting PostgreSQL:

```bash
.venv/bin/python -m pytest tests/unit
```

Bootstrap runs the same unit suite, including the pinned Psycopg binary import
check. Unit tests use temporary files and test doubles instead of real database
connections or Docker operations.

After provisioning staging, run the complete suite from the staging checkout:

```bash
.venv/bin/python -m pytest -v
```

To run only the database integration suite:

```bash
.venv/bin/python -m pytest -v tests/integration
```

Database tests require the designated, verified staging environment. A shared
safety guard checks the Docker target, database connection and stored identity
before the tests and their database operations. Missing or unsafe configuration
fails the tests rather than skipping them. The container persistence test
stops and removes only the verified staging container, recreates it using
`setup`, verifies data, roles, identity and connectivity, and removes only its
own test fixtures. Persistent storage is never deleted. Do not run these tests
against development or production.

The test suite currently covers environment management; application schema and
API tests are added within their authorized stages.

## Project Documentation

- [Functional Requirements](FUNCTIONAL_REQ.md)
- [Technical Requirements](TECHNICAL_REQ.md)
- [Coding Conventions](CODING_CONVENTIONS.md)
- [Testing Governance](TESTING.md)
- [Test Specification](TEST_SPECIFICATION.md)

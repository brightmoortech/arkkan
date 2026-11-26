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
below. Application database initialization is a separate operation, described
under Application Database Initialization.

For ordinary application connections, the configuration code uses standard
libpq process environment variables. `PGDATABASE` and `PGUSER` are required;
optional values follow libpq defaults when omitted. The resource API configuration helper does not
load `.env` automatically. The provisioning configuration validator does not
open a database connection or alter any files.

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

## Application Database Initialization

Stage 2 was accepted on November 24, 2026. Stage 3 implements all 16 PostgreSQL
resource operations, including the three `get_resource_content` signatures.
Migrations 013–036 add private helpers and public functions; migration 037
grants schema usage and appropriate function execution to `arkkan_admin` and
`arkkan_user`. Ordinary roles have no direct application-table or private-helper
access. Stage 4 WP2 provides Python read wrappers, and WP3 adds resource/type
administration wrappers. WP4 completes the Python API with lifecycle/deletion
wrappers. WP5 adds real PostgreSQL integration tests for all 16 Python operations.
See the [Stage 4 execution report](TEST_EXECUTION_PHASE1_STAGE4.md) for results,
revisions and limitations. Stage 4 acceptance is deferred until owner CLI testing.
Stage 5 WP1–WP3 implement all 16 CLI mappings, including lifecycle/deletion.
WP4 adds real CLI database tests; WP5 covers cumulative regression.

The cumulative inventory is 37 migrations. See the
[Stage 3 execution report](TEST_EXECUTION_PHASE1_STAGE3.md) for the tested
checkpoint, results and acceptance status. Use the provisioned development
instance for manual initialization and staging for automated database tests.

From the configured development checkout, with the environment verified by
`manage_environment.py check`, run:

```bash
.venv/bin/python scripts/init_db.py
```

This is a dry run, equivalent to `--check`. It checks PostgreSQL compatibility,
superuser privileges, local environment identity, and all ordered migration
steps without writing to the database. Review the target and the `PENDING`
and `UNCHANGED` results. On a compliant Stage 3 WP4 database, the Stage 3 WP5
dry run should report migrations 001–036 unchanged and 037 pending. On a compliant Stage 2
database, migrations 013–037 should be pending. Apply only after verifying the
intended target and reviewing the plan:

```bash
.venv/bin/python scripts/init_db.py --apply
```

The utility reads the checkout's existing `.env` and its configured client
password file. Do not create new credentials for initialization. For operation
without a local `.env`, supply the standard libpq process environment settings
and protected client password file; the target database must already exist.
Never supply passwords on the command line. Conflicting process connection
settings are rejected when `.env` is present.

The project-independent workflow is in
[`_migration_workflow.py`](../src/arkkan/_migration_workflow.py), with connection
prerequisites in [`_initialization_connection.py`](../src/arkkan/_initialization_connection.py).
[`_db_migrations.py`](../src/arkkan/_db_migrations.py) defines the ordered
application-specific migration checks and actions using
[`sql/migrations/`](../sql/migrations/). Add new migration steps only within the
authorized implementation stage. No migration tracking table is used.

`--apply` reuses compliant objects and commits each successfully verified
step. It stops on conflicting definitions instead of replacing them. Existing
seed descriptions and role credentials are preserved. After failure, inspect
the reported step and run the dry run again before retrying. Previously
committed steps remain; do not assume an interrupted commit succeeded or failed.
The application roles are created without passwords; the operator sets their
passwords separately before password-authenticated API or CLI use. The script
does not create databases, provision containers, or modify environment identity.

## Manual Development Database Backup and Restore

This procedure creates a logical backup of the entire development database and
restores it to a new, separate recovery database on the verified development
PostgreSQL instance. It does not replace the active database, restore cluster-wide
roles or passwords, or change the configured environment identity. The recovery
database is an inspection copy, not a provisioned application or staging target.
The procedure uses the PostgreSQL 18 client tools already in the pinned image.
The commands below use the validated local development configuration; adjust
only after verifying the corresponding environment settings.

### Back up

From the development checkout, stop application writes for the duration of the
backup and comparison. Verify the environment before proceeding:

```bash
.venv/bin/python scripts/manage_environment.py check
```

If any command fails, stop and inspect the error before proceeding. Use the
local Docker context. The examples use the container's local Unix socket as
its operating-system `postgres` user and the configured database superuser.
If local authentication is unavailable, stop; do not weaken authentication or
change credentials to execute a backup.

Run the following in your shell (use a fresh timestamped filename):

```bash
umask 077
backup_dir="$HOME/development/data/arkkan/develop/backups"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
backup="$backup_dir/arkkan_dev_$(date +%Y%m%d_%H%M%S).dump"
```

Confirm the file does not already exist. The subshell below refuses to overwrite
an existing archive. It uses no terminal allocation, preserving the binary dump.

```bash
(set -C; docker exec -u postgres arkkan-db-dev \
    pg_dump --no-password -U postgres -d arkkan_dev --format=custom > "$backup")
```

Only if the command succeeds, inspect the archive catalog:

```bash
docker exec -i -u postgres arkkan-db-dev pg_restore --list < "$backup"
```

A catalog listing is not proof of recoverability. Do not use a partial archive
from a failed backup. Keep backups outside Git and the PostgreSQL data directory;
protect them as sensitive prompt data. This database-level dump does not contain
cluster-wide role definitions, role passwords, host configuration, or credential
files. Recovery onto a different cluster requires separate role and infrastructure
preparation and is outside this local procedure.

### Restore and verify

Use the same shell session and the verified development container. Create a new
empty database using `template0`; the name must not already exist. If creation
fails, stop rather than reusing an existing database. The roles referenced by
this dump already exist on the source cluster.

```bash
docker exec -u postgres arkkan-db-dev createdb --no-password \
    -U postgres --maintenance-db=arkkan_dev --template=template0 \
    arkkan_dev_recovery
```

Restore only into the new recovery database. Do not use `--clean` or `--create`.
The restore is atomic; on failure the new database remains and requires operator
inspection before any retry.

```bash
docker exec -i -u postgres arkkan-db-dev pg_restore --no-password \
    -U postgres -d arkkan_dev_recovery --exit-on-error \
    --single-transaction < "$backup"
```

Inspect both databases using these read-only queries. In each, verify the
`development` identity, three application tables, row counts and the protected
seed slugs. Compare results with writes still stopped; also inspect representative
resource metadata and content if present, without publishing sensitive data.

```bash
(
for db in arkkan_dev arkkan_dev_recovery; do
    docker exec -u postgres arkkan-db-dev psql -X --no-password \
        -U postgres -d "$db" -v ON_ERROR_STOP=1 \
        -c 'SELECT current_database(), environment_type FROM arkkan_env.environment_identity;' \
        -c 'SELECT count(*) FROM arkkan.resource_types;' \
        -c 'SELECT count(*) FROM arkkan.resource_definitions;' \
        -c 'SELECT count(*) FROM arkkan.resource_versions;' \
        -c 'SELECT slug, is_system FROM arkkan.resource_types ORDER BY slug;' || exit 1
done
)
```

If either query sequence fails, stop and inspect before proceeding. Verify the
original environment and its application initialization from the development
checkout:

```bash
.venv/bin/python scripts/manage_environment.py check
.venv/bin/python scripts/init_db.py
```

Expect a successful environment check and all installed migration steps
`UNCHANGED` (37 after Stage 3 has been applied).
Record the backup and restore exit status and comparison outcome. Resume
application writes only after verification. Keep the recovery database separate:
never point `.env`, initialization, or automated tests at it. Its copied identity
is not independent provisioning evidence. Any eventual removal of the recovery
copy is a separate, explicit operator action after verifying its name and target;
this procedure does not drop any database. Retain the original backup according
to operator needs. Full-cluster disaster recovery, retention policies and automated
recovery remain future production-readiness work.

**Validation status:** procedure documented; execution on the local Mac is pending.

## Automated Tests

Stage 4 WP1 adds the internal execution boundary in `src/arkkan/_api.py`.
It reads process configuration for each call, binds SQL parameters, preserves
decoded JSON responses, commits successful operations, and rolls back rejected
operations. Connections are closed on failures and interruptions; commit failures
are not retried automatically because their outcome may be uncertain. Database
diagnostics are translated into safe error envelopes. Stage 4 WP2 exports four
read functions from `arkkan`, implemented in `src/arkkan/_read.py`. An internal
sentinel distinguishes omitted arguments from explicit nulls. Wrappers reject
unsupported Python types and mode-without-version calls locally; PostgreSQL
retains value validation, authorization and retrieval policy. See the
[Python API reference](../README.md#python-api-reference) for usage. WP3 adds five
administration functions in `src/arkkan/_write.py`, exported from `arkkan`.
Metadata changes use Psycopg's JSONB adapter with a copy of the caller's dictionary;
omitted keys and explicit null values remain distinct. Python checks types;
PostgreSQL validates keys, resource/type rules, permissions and state policies.
WP4 adds the seven lifecycle/deletion wrappers in the same module, completing
all 16 public operations. Text arguments remain literal; the single-version
force option accepts booleans or SQL NULL, with null rejected by SQL. Bulk
operations have no force option. Stage 5 CLI progress is described below.

The WP1 tests in `tests/unit/test_api.py` use driver doubles. They cover cleanup,
error translation, response validation and configuration without connecting to
PostgreSQL. Real Python-to-PostgreSQL integration remains a Stage 4 acceptance
requirement; these unit tests do not establish it. WP2 adds `tests/unit/test_read.py`
for public exports, exact argument routing, response preservation and malformed
calls. WP3 adds `tests/unit/test_write.py` for administration argument routing,
defaults, JSONB serialization, dictionary preservation and invalid inputs. These
suites run without PostgreSQL. WP4 adds `tests/unit/test_lifecycle.py` for the
complete export set, lifecycle/deletion routing, strict force typing, safe type
errors, response preservation and malformed calls. It also runs without PostgreSQL.

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

Application initialization integration tests reset only the known application
objects and roles in the verified staging instance; do not use staging for
data that must be retained. Resets preserve the independent environment
identity and persistent storage, and reject unexpected dependencies rather
than using cascading drops. Stage 3 tests cover the public SQL API, lifecycle
rules, concurrency, rollback and role permissions.

## Python API Integration Validation

Stage 4 WP5 adds `tests/integration/test_python_api.py`. It initializes and resets
application objects with the existing staging helpers, provisions temporary
admin/reader passwords and a mode-0600 temporary client password file, and calls
the public Python API using real Psycopg connections. Operator credential files
are never changed. Each API connection is preceded by staging verification and
checked for closure afterward. The safety hook checks runtime connection options;
it does not replace database execution or authentication with a test double.

Run the focused suite from a clean staging checkout of the committed revision:

```bash
.venv/bin/python -m pytest tests/integration/test_python_api.py -q
```

The Stage 4 regression requires `tests/unit` and all `tests/integration`.
Stage 5 adds `tests/e2e`, described below, to cumulative regression.
Do not run concurrent database suites or retain valuable application data in
staging: the fixtures reset application objects and roles before and after tests.
The Stage 4 inventory is 592 unit and 85 integration cases. For reproducible
validation, record the selected commit and save JUnit evidence:

```bash
.venv/bin/python scripts/manage_environment.py check
.venv/bin/python -m pytest tests/unit tests/integration -q --junitxml=/private/tmp/arkkan-validation.xml
.venv/bin/python scripts/manage_environment.py check
```

These commands are a validation recipe, not evidence of a new run. Consult the
[Stage 4 execution report](TEST_EXECUTION_PHASE1_STAGE4.md) for actual commands,
results and tested revisions. Its cumulative run encountered an unavailable host
port during container recreation; later guarded setup and the affected tests
passed. If this recurs, inspect the target and port owner before retrying setup;
never bypass the staging guard or remove unrelated infrastructure.

## CLI Development and Validation

`src/arkkan/_cli.py` implements the console entry point declared in
`pyproject.toml`. It uses standard-library argument parsing and calls only the
public `arkkan` API. WP1 covers read commands, help, output and exit codes.
WP2 adds creation and metadata updates, including clearing and strict UTF-8
file/stdin input. WP3 completes lifecycle/deletion commands and local coverage.
PostgreSQL retains type, state and permission enforcement.
See the [CLI reference](../README.md#cli-reference) for installation and usage.
After changing entry-point metadata, refresh the existing environment:

```bash
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m pytest tests/unit/test_cli.py tests/unit/test_cli_write.py tests/unit/test_cli_lifecycle.py -q
```

This installation command reuses the pinned dependencies installed by bootstrap.
The CLI unit suite blocks database connections, uses public API doubles, checks
exact content and JSON/error streams, and launches the installed executable's
help from a temporary working directory. The WP2 suite checks all 63 nonempty
combinations of omitted/set/empty/cleared metadata fields, preserved input bytes,
invalid UTF-8 and sanitized read failures, plus argument rejection before stdin
is consumed. WP3 checks all eight remaining mappings, literal state tokens,
force defaults/scope, zero counts, errors and help. Run the full unit suite for regression.
Local doubles do not establish role authorization or real CLI database behavior.
WP4 adds `tests/e2e/test_cli_workflows.py`, which launches the installed executable
from a temporary working directory. Each invocation verifies staging first,
supplies only the configured target and temporary admin/reader credentials, and
captures binary stdin/stdout to test exact UTF-8 and newline preservation.
There are no API or driver doubles inside the child process. Temporary password
files are created with mode 0600, checked for preservation and removed in cleanup;
operator credentials remain untouched. Application objects and roles are reset
through the shared guarded helpers before and after each case.

Refresh staging's editable installation to create its executable, then run the
focused suite from the clean staging checkout at the selected committed revision:

```bash
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m pytest tests/e2e -q
```

These cases cover creation, reads, metadata empty/null values, lifecycle and
deletion, reader denial for all writes, missing-password failure and recovery,
local-input rejection, and rollback after an injected database failure. They
reset application data; do not run concurrently with another database suite or
manual validation. Cumulative regression requires unit, integration and e2e suites.
Track package progress and actual results in the
[Stage 5 execution report](TEST_EXECUTION_PHASE1_STAGE5.md).

## Project Documentation

- [Functional Requirements](FUNCTIONAL_REQ.md)
- [Technical Requirements](TECHNICAL_REQ.md)
- [Coding Conventions](CODING_CONVENTIONS.md)
- [Testing Governance](TESTING.md)
- [Test Specification](TEST_SPECIFICATION.md)

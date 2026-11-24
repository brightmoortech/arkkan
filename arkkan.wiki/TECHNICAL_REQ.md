# `arkkan` Technical Requirements

This document specifies the architecture, PostgreSQL schema, API, security, deployment, and tests for `arkkan`. `FUNCTIONAL_REQ.md` defines resource purposes, lifecycle policies, and role permissions. PostgreSQL functions enforce the business rules; the Python API calls those functions.

## Technology

- PostgreSQL: storage, integrity constraints, permissions, transactions, and API functions. PostgreSQL 18 is the initial development and validation baseline; pin the exact release. Earlier versions are not considered supported until validated.
- Python: API used by workflows and Python-based programs. Retain Python 3.12.10; use Psycopg 3 (`psycopg[binary]`), pinned to an exact version with binary availability verified for macOS ARM64 and the target Linux architecture. Validate installation, import, PostgreSQL 18 connectivity, and password-file authentication on macOS before database implementation; validate Linux installation in Phase 2. Do not introduce an ORM.
- Linux: deployment runtime.
- macOS: development and initial testing.
- Docker: isolated PostgreSQL infrastructure for Phase 1 development and staging; container deployment of `arkkan` and container integration tests in Phase 2.

Consuming software, not `arkkan`, assembles retrieved resources into prompts. An HTTP service, graphical UI, and LLM execution are outside initial scope.

## `arkkan` Schema

The PostgreSQL schema `arkkan` contains three tables. PostgreSQL generates their UUID primary keys.

### `arkkan.resource_types`

| Column | PostgreSQL type | Requirements |
|---|---|---|
| `type_id` | `uuid` | Generated primary key; immutable |
| `slug` | `text` | Required, unique, nonblank; immutable |
| `description` | `text` | Optional; editable |
| `is_system` | `boolean` | Required; immutable; only initialization may set `true` |

Administrator-created types have `is_system = false`. Seeded types are defined under **Initialization (Phase 1)**.

The administrative deletion function must reject system types and types referenced by any Resource Definition. The PostgreSQL foreign key must independently prevent deletion of referenced types. Type descriptions may be edited, including descriptions of system types.

### `arkkan.resource_definitions`

| Column | PostgreSQL type | Requirements |
|---|---|---|
| `resource_id` | `uuid` | Generated primary key; immutable |
| `name` | `text` | Optional; editable |
| `slug` | `text` | Required, unique, nonblank; immutable |
| `description` | `text` | Optional; editable |
| `type_id` | `uuid` | Required foreign key to `resource_types.type_id`; immutable |

A Resource Definition's type is immutable after creation. Slugs are matched exactly, without automatic case conversion or normalization.

A Resource Definition can be explicitly deleted when **it has no versions** or **all its existing versions are `obsolete`**. Deleting its last version does not automatically delete the definition.

### `arkkan.resource_versions`

| Column | PostgreSQL type | Requirements |
|---|---|---|
| `version_id` | `uuid` | Generated primary key; immutable |
| `resource_id` | `uuid` | Required foreign key to `resource_definitions.resource_id`; immutable |
| `version` | `text` | Required, nonblank, unique per resource; immutable |
| `state` | `text` | Required; one of `enabled`, `enabled_default`, `disabled`, `obsolete` |
| `content` | `text` | Required; default `''`; immutable, including when empty |
| `version_info` | `text` | Optional; editable |
| `created_at` | `timestamptz` | Required; PostgreSQL-generated on insertion; immutable |

`created_at` represents the creation instant; return it as an ISO 8601 UTC timestamp. Version identifiers are opaque strings with no implied ordering. Neither identifiers nor creation times determine which version is selected.

**Database integrity:**

- Use unique constraints on `resource_types.slug`, `resource_definitions.slug`, and `(resource_id, version)`.
- Use a partial unique index on `resource_versions.resource_id` where `state = 'enabled_default'` to allow at most one default per resource, including under concurrency.
- Use checks for valid states and nonblank slugs/version identifiers (reject whitespace-only values without silently trimming or changing identifiers).
- Use foreign keys without cascading deletion. Deletion functions explicitly delete eligible versions before their definition.
- Use `BEFORE UPDATE` triggers to reject changes to immutable columns and all primary keys. The immutable columns beyond primary keys are: `resource_types.slug`, `resource_types.is_system`, `resource_definitions.slug`, `resource_definitions.type_id`, `resource_versions.resource_id`, `resource_versions.version`, `resource_versions.content`, and `resource_versions.created_at`.
- No API may provide operations that bypass PostgreSQL immutability rules.

## Environment Architecture

The Phase 1 application runs natively on macOS and connects to PostgreSQL through libpq settings. PostgreSQL deployment is independent of application deployment; no application mode or environment-specific application code is required.

Use two local checkouts of the same Git repository and one version-controlled, parameterized `compose.yaml` at the repository root. Provision separate PostgreSQL instances using the same pinned image. Do not modify unrelated Docker infrastructure.

| Setting | Development | Staging |
|---|---|---|
| Checkout | `develop/arkkan/` | `stage/arkkan/` |
| Compose project | `arkkan_develop` | `arkkan_stage` |
| PostgreSQL container | `arkkan-db-dev` | `arkkan-db-test` |
| Host | `localhost` | `localhost` |
| Host port (local validated configuration; externally configurable) | `5441` | `5442` |
| Database | `arkkan_dev` | `arkkan_test` |
| Environment identity | `development` | `staging` |

Each checkout has independent configuration, Python runtime, PostgreSQL instance, and persistent storage, as defined in Data Architecture.

Development is the only checkout used to modify source code. Staging validates a specific committed Git revision, using its own configuration and Python environment. Correct defects in development and deploy the revised commit to staging. Staging infrastructure remains stable across software revisions. See `TESTING.md` for execution and isolation rules.

### Environment Provisioning

Provide `scripts/manage_environment.py`, a shared environment management utility run from the project root using the project's Python environment:

```bash
python scripts/manage_environment.py setup
python scripts/manage_environment.py check
```

- `setup`: validate local configuration and reject unsafe directory paths and conflicting infrastructure. Create missing PostgreSQL storage and credential-parent directories without changing existing directories. If credential files are missing, report their configured paths and required permissions and stop before starting containers or initializing any database; the operator supplies them and reruns `setup`. Validate credential file prerequisites before provisioning or starting the designated PostgreSQL infrastructure, verify database readiness and connectivity, establish or verify the environment identity, and report the result.
- `check`: verify configuration, infrastructure status, readiness, connectivity, and environment identity without making changes.
- Both commands must be safe to rerun. Reject missing, invalid, or conflicting configuration rather than silently substituting environment-specific values. Reject conflicting existing infrastructure without overwriting existing data or identity. Never create or overwrite credentials, automatically delete containers, volumes or database files, or modify unrelated containers.
- Report actionable diagnostic information without exposing credentials or prompt content. Application database initialization remains a separate operation through `scripts/init_db.py`.

Comprehensive solution health checks, structured health reports, recovery diagnostics, and controlled recovery routines are backlog items; their implementation phase remains to be determined consistently with the Roadmap. Do not implement them in Stage 2.

## Data Architecture

### Data Inventory

| Data category | Source and storage | Consumer or owner |
|---|---|---|
| Resource definitions, versions, types and prompt content | PostgreSQL `arkkan` schema in persistent PostgreSQL storage | PostgreSQL API; authorized applications through the Python API or CLI |
| Database roles, authentication state and database configuration stored in the cluster | Persistent PostgreSQL storage | PostgreSQL; privileged operator |
| Environment identity | `arkkan_env.environment_identity` in the target database | Environment management utility and automated test safety guard |
| Local environment configuration | Operator-supplied `.env` for each checkout | Docker Compose, environment management utility and processes using libpq connection settings |
| PostgreSQL provisioning password | External file identified by `POSTGRES_PASSWORD_FILE` | PostgreSQL container initialization |
| PostgreSQL connection credentials | Client password file identified by `PGPASSFILE` or the libpq default | Psycopg and PostgreSQL client tools |
| Software, dependency manifests, configuration templates, Compose definition, migration SQL and seed definitions | Version-controlled repository | Development, provisioning and application initialization |
| Test fixtures and test execution evidence | Version-controlled tests and project documentation (`arkkan.wiki/`); temporary test state in staging PostgreSQL or temporary filesystem directories | Automated test harness and reviewers |
| Audit log data (planned, Phase 3) | Future PostgreSQL audit log schema | Authorized audit consumers; contracts remain to be defined |

### Data Storage and Persistence

All containers must be disposable. Removing and recreating a container must not lose persistent data, database roles, environment identity or configuration. Reproduce containers from version-controlled definitions and pinned images; keep persistent data, environment configuration and credentials outside containers.

Bind-mount PostgreSQL storage from an externally configured `POSTGRES_DATA_DIR` into the pinned PostgreSQL image's supported persistent storage location. Development and staging must use independent storage directories outside their software checkouts, under the following local directory convention:

| Environment | PostgreSQL storage |
|---|---|
| Development | `Development/data/arkkan/develop/postgres/` |
| Staging | `Development/data/arkkan/stage/postgres/` |
| Production | Operator-defined persistent location; may be `mnt/postgres/` within a persistent deployment directory |

`Development/` denotes the local workspace root, not a hardcoded application path. Resolve the configured storage location independently of disposable containers and, for development and staging, independently of software checkouts. Production storage layout is finalized during deployment planning; upgrades must not remove its persistent storage. Do not share storage between PostgreSQL instances. Environment management must never automatically delete persistent storage.

### Data Flows

1. The operator supplies environment configuration. The environment management utility validates it and prepares missing directories as defined under Environment Provisioning. The operator supplies any missing protected credential files. Once prerequisites pass, Docker Compose uses the infrastructure settings to provision or start the designated PostgreSQL instance with its external storage.
2. On first initialization of empty PostgreSQL storage, the container uses the provisioning password file to establish the initial superuser credential. PostgreSQL retains database state and credentials in its persistent storage. The environment management utility connects to the target database using privileged client connection settings to establish or verify environment identity.
3. Application initialization uses the deployment superuser's client credentials and ordered migration and seed files to create the application schemas, roles and data. It does not create or change environment identity.
4. Consuming software or the CLI calls the Python API, which uses Psycopg and the configured client credentials to call PostgreSQL API functions. PostgreSQL enforces resource policies and returns JSONB; Python returns the decoded JSON object. Consuming applications assemble prompts, not `arkkan`.
5. Automated database tests use staging connection settings and verify the independently stored environment identity before test execution, setup or cleanup. Test data is established by the test harness and evidence is retained under the approved testing governance.

### Configuration Management

Maintain one version-controlled, secret-free `.env.example` defining the application connection and Compose provisioning configuration contract. Each checkout has its own local `.env` and `.venv/`, excluded from Git. Load the selected local configuration into the execution environment. Environment-specific values, including database names, storage and credential paths, must not be hardcoded in source code. The production database name is determined during deployment planning.

Use standard PostgreSQL/libpq settings for connections: `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSFILE` when a password file other than the libpq default is used. Initialization and CLI operation require `PGDATABASE` and `PGUSER`; initialization defaults `PGPORT` to `5432`, and CLI host and port defaults follow libpq. Provisioning uses the explicitly configured environment settings and rejects missing, invalid or conflicting values rather than silently substituting environment-specific values. Configuration must distinguish the Compose project, instance, target database, storage location and expected environment identity. The project supplies a pinned Python dependency manifest; CLI/API and setup tooling run in the corresponding project virtual environment.

### Credential Management

Keep passwords out of `.env`; it contains non-sensitive settings and credential file paths. Use separate protected local files for container provisioning (`POSTGRES_PASSWORD_FILE`) and PostgreSQL client authentication (`PGPASSFILE`, or `~/.pgpass` by default on macOS and Linux). Client credentials must match the actual PostgreSQL role credentials used for a connection. Separate privileged setup credentials from ordinary API credentials.

The provisioning password file establishes the initial superuser password when PostgreSQL storage is first initialized. Recreating the container against existing storage retains the existing database password; editing the provisioning file does not rotate it. Environment management reports authentication failures rather than attempting automatic password synchronization. Password rotation is the operator's responsibility. Credential ownership, protection and access restrictions are defined in Security.

### Environment Identity

Provision `arkkan_env.environment_identity` independently of the application schemas. It contains exactly one record identifying the database as `development`, `staging`, or `production`. Enforce the singleton and allowed values in PostgreSQL; establish the record during initial environment provisioning. The record is immutable after creation; protection and privileged access are governed by Security.

On subsequent `setup` runs verify that the stored identity matches the configured environment. Abort on any mismatch; never overwrite an existing identity. A missing, invalid, or unreadable identity in an existing provisioned environment must not be treated as permission to recreate it. `check` verifies the identity without creating it.

Keep this schema independent of `arkkan` and `arkkan_api` so that application initialization tests can start without either application schema and safety verification can occur before any application reset. Automated database tests, setup, and cleanup must verify the designated staging instance and its stored `staging` identity before proceeding. The guard must fail closed and have no force option or bypass. See `TESTING.md`, Section 5, for test safety enforcement.

### Data Lifecycle

Resource Metadata and Resource Versions follow the creation, modification, state transition and deletion contracts specified in the `arkkan` Schema and API sections. PostgreSQL is the authoritative store. Application initialization seeds protected resource types without overwriting administrator-edited descriptions. Staging tests establish and reset application schema and test data to known states as required; they must preserve environment identity. Persistent storage is not disposable merely because its container is disposable. Audit log data lifecycle and retention remain to be specified in Phase 3.

### Backup and Recovery

Include a basic, documented manual database backup-and-restore procedure during local development. Container recreation is not a substitute for backup or recovery. Production recovery objectives, retention, automated recovery, replication and failover remain to be defined during production readiness (Phase 4).

## Initialization (Phase 1)

Initialization is a separate privileged setup operation, **not** an `arkkan` CLI subcommand. It prepares an existing PostgreSQL database for normal API access. Use a version-controlled Python entry point, `scripts/init_db.py`, backed by ordered SQL migration files. Run it from the project root using the project's Python environment:

```bash
python scripts/init_db.py
python scripts/init_db.py --check
python scripts/init_db.py --apply
```

The default invocation is a dry run. `--check` explicitly selects the same read-only behavior: validate prerequisites and report pending setup or mismatches without changing the database. Only `--apply` performs pending setup. These options are mutually exclusive. Report success or a specific failure; an invalid or unrecognized argument fails without making changes.

Separate the project-independent initialization workflow (connection and prerequisite checks, planning, ordered execution, transaction management, verification and reporting) from application-specific migration definitions and SQL files. Each migration provides a read-only check for missing, compliant or conflicting objects, applies only missing work, and verifies its expected state before committing. The workflow uses the same checks to plan all migrations before any application changes and to verify the final state.

### Prerequisites and configuration

- PostgreSQL is installed, running, and the **target database already exists**. Database server installation and database creation are external prerequisites; the script must not create or drop databases. For the Phase 1 local environments, complete Environment Provisioning first. Application initialization does not create, modify, or remove the environment identity.
- Run initialization using the existing deployment PostgreSQL superuser. Its role name is not fixed. Do not use `arkkan_admin` or `arkkan_user` for initialization.
- Supply the PostgreSQL connection settings and privileged client credentials defined in Data Architecture. `PGDATABASE` and `PGUSER` are required; run using the project virtual environment. For a configured local checkout, initialization reads `.env` without executing it, rejects conflicting process connection settings, and verifies its stored environment identity without changing it. Otherwise, supply standard PostgreSQL connection settings through the process environment. Never pass passwords as script options.

### Execution sequence

1. Connect to the target database using the supplied superuser credentials. Verify PostgreSQL compatibility and required privileges. Reject missing prerequisites before changing anything.
2. Inspect existing database objects and compare them with the expected definitions. If existing objects conflict with the specification, **abort with a specific discrepancy**; do not silently drop, replace, or overwrite them.
3. Apply pending migrations in dependency order: access roles (`arkkan_admin`, `arkkan_user`); schemas (`arkkan`, `arkkan_api`); tables and constraints; integrity triggers; PostgreSQL API functions; and access grants. Use ordered, version-controlled, idempotent SQL files. Do not introduce a fourth application table for migration tracking. Each setup step that changes schema or data must be atomic; a failure rolls back that step and stops further work. Do not claim earlier committed steps were rolled back.
4. Seed these seven protected resource-type slugs: `constraints`, `process`, `rubric`, `role`, `task`, `templates`, `extensions`. Use the corresponding descriptions from the Resource Types table in `FUNCTIONAL_REQ.md`. Keep the exact slug-to-description mapping in a version-controlled file bundled with initialization; do not parse the Markdown document at runtime. Mark seeded rows `is_system = true`.
5. Verify all seven slugs, their system flags, and expected constraints; check function permissions and the required schema objects. Report what was applied and what remains unchanged.

### Reruns and failures

- Initialization is idempotent: rerunning `--apply` with the same migration set creates no duplicate objects or seed rows. It must not overwrite administrator-edited type descriptions, including descriptions of system types.
- Seed reconciliation: insert missing system types; verify the `is_system` flag for existing seeded slugs. If an existing row has a conflicting flag or an incompatible definition, stop with an actionable error rather than silently changing it. The description from the seed file is used **only on initial insertion**.
- A failed setup step returns a nonzero exit code and leaves its changes rolled back. Do not continue to later steps. The default dry run and `--check` never write.
- Create `arkkan_admin` and `arkkan_user` as roles that can log in, without embedding passwords in SQL or source files. A privileged operator must set their passwords separately, using PostgreSQL's interactive password-setting facility (for example, `psql`'s `\password` command), before password-authenticated CLI use. Initialization must not overwrite existing role credentials.
- Restrict access to API functions as specified in **Security**. The setup script must not grant table DML privileges to normal API roles.

**Acceptance:** Automated tests must cover clean initialization, the default dry run and `--check` without writes, idempotent reruns, the seven seeded slugs and their functional descriptions, protection of seeded types, preservation of edited descriptions, conflicting-object failures, and migration rollback. Tests operate against an isolated test database, not a database containing user data.

## API

All resource operations are PostgreSQL functions exposed to Python; the Python API calls PostgreSQL functions for all operations. PostgreSQL functions enforce the business rules. Write, delete, and state operations belong to the **Admin API**.

Public SQL functions belong to schema `arkkan_api`, with matching Python method names. The call forms below use Python notation; implement corresponding PostgreSQL functions using `text`, `boolean`, and `jsonb` parameters, with SQL `NULL` for Python `None`. PostgreSQL functions return `jsonb`; Python returns the decoded JSON object. Required parameters are shown without defaults.

### Common API Contracts

**Authorization:** Read API functions permit `arkkan_user` and `arkkan_admin`; Admin API functions permit `arkkan_admin`. The deployment PostgreSQL superuser retains its administrative powers. Ordinary API roles access resource data through functions, not direct table operations.

**Version availability:** A version is **available** if its state is `enabled` or `enabled_default`. A version is **unavailable** if it is missing, deleted, `disabled`, or `obsolete`. Retrieval selection and fallback rules are defined only in `get_resource_content`.

**Response JSON:** Every completed API function returns the following common structure. The `data` value varies by operation and is defined in its **Return** section.

Success:

```json
{"operation_name":"get_resource_content","message_type":"response","result":"success","data":{"slug":"example","version":"1.0","state":"enabled_default","content":""}}
```

Error:

```json
{"operation_name":"get_resource_content","message_type":"response","result":"error","reason":"Requested resource version is unavailable."}
```

`operation_name` is the invoked function name; `message_type` is always `response`; `result` is `success` or `error`. Success includes `data`; error includes `reason`, a concise actionable explanation without secrets, prompt content, or raw SQL diagnostics. Invalid inputs, missing records, unauthorized access, and rejected state changes must not produce partial mutations. PostgreSQL may reject unauthorized execution before entering a function; the Python API translates that database error into this response format. Optional values use JSON `null` where applicable.

**Shared validation:** Reject null, blank, or whitespace-only required slugs/version identifiers; reject unknown states and retrieval modes. Match accepted identifiers exactly. Validate API input before changing data. Each mutating call is transactional. In case of error, roll back all changes. Use locking or equivalent serialization when several calls may change versions of the same resource concurrently.

### Read Operations

#### `get_resource_content`

**Function calls**

```python
get_resource_content(slug)
get_resource_content(slug, version)
get_resource_content(slug, version, mode)
```

**Purpose:** Retrieve a resource version's content.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `version` | `text` | Requested version identifier |
| `mode` | `text` | Selection mode: `strict`, `version_priority`, or `default_priority` |

**Return:** Common response JSON. Success `data`: `{slug, version, state, content}` for the version actually selected. Error if no version qualifies under the requested call.

**Behavior**

- `get_resource_content(slug)`: retrieve only the default version. Error if no available default exists.
- `get_resource_content(slug, version)`: retrieve only that version; identical to `get_resource_content(slug, version, "strict")`.
- `strict`: retrieve the specified version if available; otherwise error. No fallback.
- `version_priority`: retrieve the specified version if available; otherwise retrieve the default if available; otherwise error.
- `default_priority`: retrieve the default if available; otherwise retrieve the specified version if available; otherwise error.

**Authorization:** Read API roles.

**Other Considerations**

- Empty content (`""`) is a successful result.
- Return the **selected** version and state, including when fallback selects the default.

#### `list_resources_matching_type`

**Function calls:** `list_resources_matching_type(type_slug)`

**Purpose:** List Resource Definitions of a type.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `type_slug` | `text` | Registered resource-type slug |

**Return:** Common response JSON. Success `data`: array of `{name, slug, description}`. Error for an unknown type.

**Behavior:** Return all Resource Definitions assigned to the type, regardless of their versions' number or states. A type with no matching resources returns `[]` successfully.

**Authorization:** Read API roles.

#### `get_resource_version_default`

**Function calls:** `get_resource_version_default(slug)`

**Purpose:** Identify a resource's default version.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |

**Return:** Common response JSON. Success `data`: `{slug, version}`. Error when the resource or its default is absent.

**Behavior:** Return the version identifier whose state is `enabled_default`; do not return its content.

**Authorization:** Read API roles.

#### `get_resource_info`

**Function calls:** `get_resource_info(slug)`

**Purpose:** Retrieve resource metadata and version information.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |

**Return:** Common response JSON. Success `data`: `{slug, name, description, type_slug, versions}`, where `versions` is an array of `{version, state, created_at}`. Error for an unknown resource.

**Behavior:** Return all the resource's versions, including disabled and obsolete ones, without content. When there are no versions, return `versions: []`.

**Authorization:** Read API roles.

### Admin API — Write Operations

#### `add_resource`

**Function calls:** `add_resource(slug, version, type_slug=None, name=None, description=None, content="", version_info=None, state="disabled")`

**Purpose:** Create a resource version and, when necessary, its Resource Definition.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `version` | `text` | New version identifier |
| `type_slug` | `text`, optional | Registered resource type |
| `name` | `text`, optional | Resource display name |
| `description` | `text`, optional | Resource description |
| `content` | `text`, optional | Version content; default `''` |
| `version_info` | `text`, optional | Description of this version's changes |
| `state` | `text`, optional | Initial state; default `disabled` |

**Return:** Common response JSON. Success `data`: `{resource_id, version_id, slug, version, state, created_at}`. Error on invalid input, duplicate version, or lifecycle violation.

**Behavior**

- If `slug` does not exist, create its Resource Definition and initial version atomically; `type_slug` is required and must reference an existing type.
- If `slug` exists, add a version to it; if `type_slug` is supplied, it must match the existing type. Any supplied `name` or `description` is ignored; use `update_resource` to edit existing metadata.
- Initial state may be `disabled`, `enabled`, or `enabled_default`, never `obsolete`.
- When creating a default, demote the existing default to `enabled` in the same transaction.

**Authorization:** Admin API roles.

**Other Considerations**

- Resource content is immutable immediately, including empty content.
- Reject a duplicate `(slug, version)`; do not overwrite an existing version.

#### `update_resource`

**Function calls:** `update_resource(slug, changes, version=None)`

**Purpose:** Update resource or version descriptions.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `changes` | `jsonb` | Metadata fields and their new values |
| `version` | `text`, optional | Version identifier for `version_info` updates |

**Return:** Common response JSON. Success `data`: `{slug, updated_fields}` and `version` when supplied. Error on invalid changes or missing target.

**Behavior**

- Allowed `changes` keys: `name`, `description`, `version_info`.
- `name` and `description` update Resource Metadata; `version_info` updates the identified version.
- `version` is required if `version_info` is present. Without `version_info`, a supplied `version` is invalid.
- Reject unknown keys, empty objects, and nonexistent resource/version references.

**Authorization:** Admin API roles.

**Other Considerations**

- An omitted key leaves its value unchanged; JSON `null` clears the corresponding optional field.
- Slugs, resource type, version identifiers, content, and state are not editable through this operation.

#### `add_resource_type`

**Function calls:** `add_resource_type(slug, description=None)`

**Purpose:** Add a resource type.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | New resource-type slug |
| `description` | `text`, optional | Explanation of the type |

**Return:** Common response JSON. Success `data`: `{type_id, slug}`. Error for duplicates or invalid input.

**Behavior:** Create a new type with `is_system = false`; callers cannot set `is_system`.

**Authorization:** Admin API roles.

#### `update_resource_type`

**Function calls:** `update_resource_type(slug, description)`

**Purpose:** Edit a resource type's description.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Existing resource-type slug |
| `description` | `text` or `null` | New description |

**Return:** Common response JSON. Success `data`: `{slug, description}`. Error for unknown type or invalid input.

**Behavior:** Replace only the type's `description`, including for system types. Allow `null` to clear it; leave slug and `is_system` unchanged.

**Authorization:** Admin API roles.

#### `delete_resource_type`

**Function calls:** `delete_resource_type(slug)`

**Purpose:** Delete an unused administrator-created type.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource-type slug |

**Return:** Common response JSON. Success `data`: `{slug}`. Error if absent, protected, or referenced.

**Behavior:** Reject deletion of any system type or any type referenced by a Resource Definition; otherwise delete the type.

**Authorization:** Admin API roles.

**Other Considerations**

- A foreign key also prevents deletion of referenced types.

### Admin API — Delete Operations

#### `delete_resource_version`

**Function calls:** `delete_resource_version(slug, version)`

**Purpose:** Delete one obsolete resource version.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `version` | `text` | Version identifier |

**Return:** Common response JSON. Success `data`: `{slug, version}`. Error if the version is absent or not obsolete.

**Behavior:** Delete the version only when its state is `obsolete`; preserve the Resource Definition, including if it becomes empty.

**Authorization:** Admin API roles.

#### `delete_resource_version_all`

**Function calls:** `delete_resource_version_all(slug)`

**Purpose:** Delete all obsolete versions of one resource.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |

**Return:** Common response JSON. Success `data`: `{slug, deleted_count}`. Error for unknown resource.

**Behavior:** Delete only obsolete versions of the selected resource. If none are obsolete, return `deleted_count: 0`; keep the Resource Definition.

**Authorization:** Admin API roles.

#### `clean_up`

**Function calls:** `clean_up()`

**Purpose:** Delete obsolete versions across all resources.

**Parameters:** None.

**Return:** Common response JSON. Success `data`: `{deleted_count}`. Error if the operation fails.

**Behavior:** Delete every obsolete version atomically, preserving all Resource Definitions. If there are none, return `deleted_count: 0`.

**Authorization:** Admin API roles.

#### `delete_resource`

**Function calls:** `delete_resource(slug)`

**Purpose:** Delete a Resource Definition and its eligible versions.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |

**Return:** Common response JSON. Success `data`: `{slug, deleted_version_count}`. Error if unknown or any version is not obsolete.

**Behavior:** Delete explicitly when no versions exist, or when every existing version is obsolete. In the latter case, delete those versions and the Resource Definition atomically. Never delete the resource type.

**Authorization:** Admin API roles.

### Admin API — State Operations

The permitted individual transitions are:

| Current state | Allowed next states |
|---|---|
| `enabled` | `enabled_default`, `disabled` |
| `enabled_default` | `enabled`, `disabled` |
| `disabled` | `enabled`, `enabled_default`, `obsolete` |
| `obsolete` | `disabled` |

One version per resource may be `enabled_default` at most. Promoting a new default demotes the existing default to `enabled`. Removing a default without replacement requires `force`, which overrides **only** the default-preservation rule. No transition permits a version to remain in the same state.

#### `set_resource_state`

**Function calls:** `set_resource_state(slug, version, target_state, force=False)`

**Purpose:** Change one version's lifecycle state.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `version` | `text` | Version identifier |
| `target_state` | `text` | Desired lifecycle state |
| `force` | `boolean`, optional | Override for removing the default without replacement; default `false` |

**Return:** Common response JSON. Success `data`: `{slug, version, state}`. Error for invalid transition, absent target, or policy violation.

**Behavior:** Validate the requested transition and resulting default policy before changing the version; reject the operation if either fails. If assigning a new default, demote the prior default atomically.

**Authorization:** Admin API roles.

#### `set_resource_state_all`

**Function calls:** `set_resource_state_all(slug, target_state)`

**Purpose:** Change every version of a resource to one state.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `target_state` | `text` | Desired state for all versions |

**Return:** Common response JSON. Success `data`: `{slug, changed_count}`. Error for unknown resource or any invalid transition/policy outcome.

**Behavior:** Validate all transitions and resulting default constraints before modifying rows. Reject the entire operation if any version fails validation; otherwise change all versions in one transaction.

**Authorization:** Admin API roles.

**Other Considerations**

- No `force` option is supplied for this bulk operation.
- If the resource contains no versions, return `changed_count: 0`.

#### `set_resource_state_all_with_guard`

**Function calls:** `set_resource_state_all_with_guard(slug, source_state, target_state)`

**Purpose:** Change versions currently in one state to another state.

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `slug` | `text` | Resource identifier |
| `source_state` | `text` | State to match |
| `target_state` | `text` | Desired state for matching versions |

**Return:** Common response JSON. Success `data`: `{slug, changed_count}`. Error for unknown resource or invalid transition/policy outcome.

**Behavior:** Select only versions whose current state equals `source_state`. Validate all proposed transitions and the resulting default constraints before modifying rows. If any fails, reject the entire operation. If none match, return `changed_count: 0`.

**Authorization:** Admin API roles.

**Other Considerations**

- No `force` option is supplied for this bulk operation.

### Python Interface

Provide an installable Python package exposing the documented public functions. Use parameterized SQL calls, manage connections and transaction lifecycles safely, and read database credentials from runtime configuration. The Python API returns the decoded common JSON response and does not implement a second set of lifecycle rules.

## CLI (Phase 1)

Provide one installable executable named `arkkan` for macOS and Linux. It calls the Python API, which calls the PostgreSQL functions. The CLI does not implement resource policies or access tables directly. Use subcommands, with Unix-style short options where practical; `-h` and `--help` work at every command level. No new database operations are introduced by the CLI.

### Installation and database access

- Install the Python package in the project's virtual environment (for example, `python -m pip install -e .` from the project root). Its package entry point provides the `arkkan` command. The executable runs wherever that environment's `bin` directory is on `PATH`; do not hardcode `/usr/local/bin` or change system Python.
- The same commands and option semantics apply on macOS and Linux. System-wide exposure through `PATH` is optional and not needed for Phase 1 acceptance.
- Supply the libpq connection settings and client credentials defined in Data Architecture. The CLI requires `PGDATABASE` and `PGUSER`. Do not accept a password command-line flag.
- `PGUSER=arkkan_user` permits read functions; `PGUSER=arkkan_admin` permits read and admin functions. Authorization is enforced by PostgreSQL, not a local CLI role switch. Do not make setup/superuser operations available as CLI subcommands.

### Command reference

All positional `SLUG`, `VERSION`, `TYPE`, and `STATE` tokens are passed unchanged to the corresponding API parameters. Options are scoped to their own command. Existing API validation and defaults remain authoritative.

| Command | API function | Options and inputs |
|---|---|---|
| `arkkan resource get SLUG` | `get_resource_content` | `-v VERSION` for strict version retrieval; `-m MODE` with `-v` for `strict`, `version_priority`, or `default_priority` |
| `arkkan resource list -t TYPE` | `list_resources_matching_type` | `-t TYPE` required |
| `arkkan resource default SLUG` | `get_resource_version_default` | None |
| `arkkan resource info SLUG` | `get_resource_info` | None |
| `arkkan resource add SLUG VERSION` | `add_resource` | `-t TYPE`, `-n NAME`, `-d DESCRIPTION`, `-f FILE`, `-i VERSION_INFO`, `-s STATE` |
| `arkkan resource update SLUG` | `update_resource` | `-n NAME`, `-d DESCRIPTION`, `-i VERSION_INFO` with `-v VERSION`; clear options below |
| `arkkan type add TYPE` | `add_resource_type` | `-d DESCRIPTION` |
| `arkkan type update TYPE` | `update_resource_type` | `-d DESCRIPTION` or `--clear-description` |
| `arkkan type delete TYPE` | `delete_resource_type` | None |
| `arkkan resource delete-version SLUG -v VERSION` | `delete_resource_version` | `-v VERSION` required |
| `arkkan resource delete-obsolete SLUG` | `delete_resource_version_all` | None |
| `arkkan resource cleanup` | `clean_up` | None |
| `arkkan resource delete SLUG` | `delete_resource` | None |
| `arkkan resource state SLUG -v VERSION -s STATE` | `set_resource_state` | `-v VERSION` and `-s STATE` required; `-F` permits the API's `force` behavior |
| `arkkan resource state-all SLUG -s STATE` | `set_resource_state_all` | `-s STATE` required |
| `arkkan resource state-matching SLUG -g STATE -s STATE` | `set_resource_state_all_with_guard` | `-g` source state; `-s` target state; both required |

**Argument conventions**

- For `resource get`, no `-v` means default-only retrieval. `-v` without `-m` means strict retrieval. `-m` without `-v` is invalid. Mode names are exact API values.
- `resource add`: `-t` is required only when `SLUG` is new; if supplied for an existing resource, it must match the existing type. `-s` defaults to `disabled`. Omitted `-f` supplies empty content. `-f FILE` reads the complete UTF-8 file contents; `-f -` reads UTF-8 standard input. Neither form alters the source file. Reject file-read failures and invalid UTF-8 before calling the API. `-n` and `-d` apply to a new Resource Definition only, as specified by `add_resource`.
- `resource update`: use `-n` and `-d` for Resource Definition metadata; use `-i` with `-v` for version information. `--clear-name`, `--clear-description`, and `--clear-info` send JSON `null` for their corresponding fields; each is mutually exclusive with its setter. `--clear-info` requires `-v`. Do not submit omitted fields. Reject commands with no updates or with `-v` but no version-information update. Do not confuse an empty argument (`-d ''`) with clearing a field (`--clear-description`).
- `type update`: specify exactly one of `-d` or `--clear-description`. The latter passes JSON `null`; an empty `-d ''` supplies an empty string.
- `-F` is available only on `resource state`. It does not bypass invalid state transitions or other lifecycle policies.
- `-j` selects JSON output on **every operational command**. `-h` / `--help` prints usage without connecting to PostgreSQL.

### Output and errors

- Default output is human-readable. `resource get` prints **only** the retrieved content to standard output, without headings or metadata; an empty content string succeeds with no content output. Other commands print a concise result including identifying fields or counts as appropriate.
- With `-j`, write the complete common API response JSON (including `data` or `reason`) to standard output. Do not duplicate this JSON schema in CLI documentation.
- Report human-readable errors on standard error, never mixing errors with resource content. Use exit code `0` for success, `1` for API/authorization/database failures, and `2` for command syntax or local input errors. For `-j`, write the normalized API error JSON to standard output when an API response exists, while still returning a nonzero exit code. CLI-only parsing errors may use standard error without a JSON envelope.
- Reject unknown subcommands/options, missing required values, conflicting setters/clearers, and invalid argument combinations **before** making database calls. `arkkan -h`, `arkkan resource -h`, `arkkan type -h`, and each individual command's `-h` must show relevant help.

**Acceptance:** Tests must cover every command-to-API mapping, option combinations and defaults, standard output versus standard error, JSON output, exit codes, help, role-based authorization, password-file use, UTF-8 content files, standard input, empty content, and metadata clearing. Run CLI integration tests against an isolated PostgreSQL database and separately test local argument handling without a database connection.

## Security

The existing PostgreSQL superuser (its name depends on deployment) owns and manages the `arkkan` schema, tables, and functions; no separate owner role is required.

| Functional Role | PostgreSQL Role | Create Table | Modify Table | Drop Table | Add Row | Edit Row | Delete Row | Read | Generate View |
|---|---|---|---|---|---|---|---|---|---|---|
| `superuser` | Existing PostgreSQL superuser | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `arkkan admin` | `arkkan_admin` | No | No | No | Yes | Yes | Yes | Yes | Yes |
| `arkkan user` | `arkkan_user` | No | No | No | No | No | No | Yes | Yes |

Roles specify allowed capabilities, not direct table grants. Only the PostgreSQL superuser has schema-level modification authority. `arkkan_admin` and `arkkan_user` receive `EXECUTE` permissions on appropriate API functions, **not direct table write permissions**. Revoke unwanted default `PUBLIC` privileges, including execution of privileged functions. Restrict internal helper functions and do not allow callers to bypass API enforcement. Apply least privilege to schema usage and connections.

Use controlled SQL and qualified names in privileged functions; set a safe function `search_path`. Do not interpolate caller-provided identifiers into dynamic SQL. Keep credentials out of source code and logs and limit network exposure.

**Generate View** appears in the permissions matrix but has no defined function contract. Do not fabricate an API operation; it requires separate specification before implementation.

### Credential and Environment Identity Protection

The environment operator creates and manages both password files. The environment management utility validates their existence and permissions without exposing their contents; it must never create, modify, overwrite or synchronize credentials. Require file permissions `0600` for the client password file; protect the provisioning password file from unauthorized access. Exclude credential files from Git. Initialization must not create, print or modify password files. CLI tooling must not store passwords in CLI configuration or print them; do not embed passwords in SQL, source, repositories, container images or logs. The privileged operator sets or rotates PostgreSQL role passwords separately, as described under Initialization.

Protect `arkkan_env.environment_identity` against subsequent modification, insertion, deletion or removal by ordinary roles. Application roles must not be able to alter or remove the environment metadata. The deployment superuser retains its administrative powers; control privileged access. Automated tests must not bypass the staging identity guard.

## `arkkan` Log Schema (Phase 3)

Two audit log classes are planned:

1. **Read logs:** identity of who attempted to retrieve prompt content; slug/version; pass/fail; timestamp; originating IP. Metadata-only lookups are excluded.
2. **Change logs:** identity of who successfully modified a resource; change details; timestamp; originating IP.

Caller identity, trusted IP attribution across container networking, and the controlled method by which `arkkan_user` causes log entries to be written remain to be defined. Phase 3 audit tables and operations are not part of the initial release.

## Development & Deployment

### Roadmap

| Phase | Scope | Completion criteria |
|---|---|---|
| **1. Working Local Prototype** | PostgreSQL schema, roles, SQL functions, Python API, CLI, and automated tests on macOS, with isolated PostgreSQL infrastructure before containerization of `arkkan`. | All approved in-scope functions work through PostgreSQL and Python; CLI operations and local integration tests pass. |
| **2. Containerization** | Docker deployment, automated container builds and initialization, persistent storage, and container integration tests. | Phase 1 functionality works in containers without changing its business rules. |
| **3. Audit Logging** | Read and change log schemas, caller identity, attribution, and logging enforcement. | Audit logging requirements are defined and validated with automated tests. |
| **4. Production Readiness** | Ready-to-use PostgreSQL backup/restore, disaster-recovery, redundancy, and failover configurations, with recovery testing. | Recovery and failover configurations are documented and tested against defined recovery objectives. |
| **5. Backlog Enhancements** | Deferred capabilities, including recipe-based prompt assembly and environment management enhancements not assigned to an earlier phase. | Each enhancement is specified and prioritized before implementation. |

Phase 1 is a working prototype, not a disposable implementation. Production readiness is deferred. Prompt assembly remains the responsibility of consuming software; recipes are not part of the current implementation scope.

### Phase 1 Implementation Strategy

Implement Phase 1 in the following stages. Supply the coding LLM with the complete Functional Requirements, Technical Requirements, and Software Architectural Principles at the outset, but authorize implementation **one stage at a time**. Do not begin the next stage until the current stage meets its validation gate.

| Stage | Deliverable | Validation gate |
|---|---|---|
| **1. Project Foundation** | Python project structure, pinned dependencies, virtual environment guidance, configuration, and test harness. | Package installs in a clean environment; configuration validation and initial tests run. |
| **2. Database Foundation** | Isolated development and staging PostgreSQL environments, shared Compose configuration, `scripts/manage_environment.py`, environment identity and test safety guard; database roles, schemas, tables, constraints, triggers, seed data, and the initial `scripts/init_db.py` setup framework. | Environment provisioning, container recreation with persistent data, identity protection, driver compatibility, and safety tests pass; schema and seed tests pass in the isolated staging PostgreSQL database; the default dry run and `--check` are read-only and applicable setup steps are idempotent. Full initialization is not yet complete. |
| **3. PostgreSQL API** | All specified SQL functions, grants, and remaining initialization migrations. | Function integration and role-permission tests pass; full clean initialization, rerun, and failure/rollback tests pass. |
| **4. Python API** | Python wrappers for the PostgreSQL functions and the common JSON response contract. | Unit and PostgreSQL integration tests pass for all specified operations and errors. |
| **5. CLI** | The `arkkan` command and subcommands, options, help, authentication, and output handling defined in the CLI section. | CLI argument, output, authorization, and end-to-end command tests pass. |
| **6. End-to-End Validation** | Complete Phase 1 workflow verification and setup/usage documentation. | All Phase 1 acceptance tests pass on macOS, including fresh setup and representative successful and failed workflows. |

**Execution controls:**

- At each stage, implement only the authorized scope; consult the full specifications to preserve compatibility with later stages. Do not invent requirements or public APIs.
- Resolve material conflicts or unspecified behavior through the prescribed clarification process before implementing the affected behavior. Do not reconfirm requirements already defined.
- Perform **two review-and-correction passes per stage**: (1) requirements coverage and correctness; (2) code quality, consistency, maintainability, and regression risks. Run the relevant tests and report actual results before requesting authorization for the next stage.
- Create a Git checkpoint after each validated stage. Do not treat an incomplete stage or an untested implementation as complete.
- Treat Stage 2 as a foundation for initialization, not its completion. Stage 3 completes and validates the Initialization (Phase 1) contract after the API functions exist.

### Cross-Phase Requirements

- Develop and initially test `arkkan` on macOS using the isolated PostgreSQL infrastructure defined in Environment Architecture. Linux Docker deployment of `arkkan` begins in Phase 2.
- Use the **Initialization (Phase 1)** procedure for database setup in each deployment environment.
- Pin applicable dependencies to identifiable versions.
- In Phase 2, automate container builds, initialization, startup, and integration tests using the persistence and configuration contracts in Data Architecture.

### Testing and Acceptance

**Phase 1 automated PostgreSQL/Python tests** must cover:

1. Database schema integrity, including foreign keys and uniqueness. Initialization tests are specified under **Initialization (Phase 1)**.
2. Type description updates (including protected types), slug/flag immutability, custom type creation, and restrictions on deletion.
3. Definition slug/type immutability and name/description updates; version identifier, content, and `created_at` immutability; editable `version_info`; empty content.
4. All allowed and forbidden state transitions, default promotion, force-only default removal, and transactional rollback.
5. All `get_resource_content` call forms and each selection mode, covering unavailable versions, absence of defaults, and empty content.
6. Read operations on resources with active, disabled, obsolete, or zero versions; error and success JSON structures.
7. Single, bulk, and global obsolete-version deletion; explicit Resource Definition deletion both when empty and when all versions are obsolete.
8. Concurrent default changes and atomic bulk state changes; unchanged records after rejection.
9. Role-level function permissions, denial of direct writes, protected internal functions, and Python error translation.
10. Python wrappers, input validation, null versus omitted metadata changes, and rejection of malformed calls.
11. CLI behavior and its interaction with the Python API under **CLI (Phase 1)**, including all documented commands, help, authorization, and output modes.

**Stage 2 environment tests and validation** must cover configuration validation and rejection of conflicts, independent Compose projects and storage, directory preparation before requesting missing credentials, reuse of existing directories without modification, read-only rejection of missing credentials by `check`, credential file validation without disclosure, driver installation/import and PostgreSQL connectivity with password-file authentication, successful provisioning and safe reruns, read-only `check`, readiness failures, preservation of existing data and unrelated infrastructure, singleton identity creation and protection, rejection of identity mismatches, and mandatory test safety rejection for development, production, missing, invalid, or unreadable identity and incorrect target connection settings. Verify that application resets preserve identity and that tests do not depend on retained test data. Verify that removing and recreating the designated staging PostgreSQL container with its configured external storage preserves database contents, roles, environment identity and configuration; verify connectivity after recreation. Perform this controlled test only after the staging safety guard succeeds; do not delete persistent storage or affect unrelated infrastructure.

**Phase 2 tests** must rerun applicable Phase 1 tests inside Docker and verify deployment initialization, restart behavior, and persistent storage.

Do not report test passes without executing the tests.

### Implementation Notes for Code Generation

- Implement schema integrity protections first; then PostgreSQL API functions; then the Python wrapper, CLI, and integration tests.
- Use the exact names, contracts, and common JSON response structure in this document. Do not add public operations that are not specified.
- Treat each mutation as one transaction, including default replacement and bulk actions. For concurrent updates to a resource, serialize access to that resource (or use an equivalent strategy) and keep database uniqueness constraints as a backstop.
- Version identifiers and timestamps must never be interpreted as automatic version ordering.
- Use PostgreSQL as the policy enforcement boundary. No current or future API may bypass its immutability and state rules.
- Defer Generate View and Phase 3 audit attribution until their contracts are specified.

# arkkan Test Specification

Test governance is defined in `TESTING.md`. Test cases map to the applicable
sections of `TECHNICAL_REQ.md`. This specification covers only the authorized
implementation scope and expands with subsequent stages. Each test identifier
denotes an executable test function. Parameterized functions exercise multiple
cases under the same identifier; test collection and execution report the
expanded cases.

## Phase 1, Stage 1: Project Foundation

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S1-001 | Phase 1 Implementation Strategy: package installs in a clean environment | `tests/unit/test_import.py::test_s1_001_package_import`: package imports. Stage 4 checks public exports separately in S4-010. Run after clean bootstrap for installation evidence. |
| S1-002 | Initialization / Prerequisites and configuration; CLI / Installation and database access | `test_s1_002_required_settings`: valid PGDATABASE and PGUSER are accepted. |
| S1-003 | Same configuration requirements; Stage 1 configuration validation | `test_s1_003_required_validation`: each required setting is rejected when missing, empty or whitespace-only; error identifies the variable. |
| S1-004 | Initialization / Prerequisites and configuration; CLI / Installation and database access | `test_s1_004_optional_settings`: optional PGHOST, PGPORT and PGPASSFILE are preserved; omitted settings are not added (also covered by S1-002). Actual libpq default resolution is not tested at Stage 1. |
| S1-005 | Security; Cross-Phase Requirements | `test_s1_005_preserve_values_and_exclude_credentials`: identifiers are preserved and unrelated variables and passwords are not returned. |
| S1-006 | Cross-Phase Requirements: externally configurable connections | `test_s1_006_process_environment`: configuration reads the process environment by default. |

Configuration tests are in `tests/unit/test_config.py`. They do not open a
database connection or read password files. Real PostgreSQL connectivity and
password-file authentication for environment management are covered by the
Stage 2 environment integration cases. Application initialization and CLI
authentication coverage are added at their respective implementation stages.

The full Stage 1 validation gate also requires running `./scripts/bootstrap.sh`
with a clean virtual environment on macOS using Python 3.12.10 and the pinned
dependencies. Bootstrap must complete package installation, dependency checks
and the initial pytest suite successfully. This environment-level gate is not
established by a source-only import test.

## Phase 1, Stage 2: Database Foundation

### Environment foundation

All automated cases below are in `tests/unit/test_environment.py`. Filesystem
fixtures use temporary directories and synthetic values; these tests do not
connect to PostgreSQL or start Docker.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S2-001 | Data Architecture / Configuration Management | `test_s2_001_literal_configuration`: parse supported assignments without executing shell code. |
| S2-002 | Configuration Management; Security | `test_s2_002_reject_invalid_configuration`: reject duplicates, unsupported keys and invalid syntax without disclosing values. |
| S2-003 | Environment Provisioning | `test_s2_003_valid_contract_does_not_write`: accept valid configuration without creating storage or changing credential files. |
| S2-004 | Environment Provisioning; Data Architecture / Configuration Management | `test_s2_004_missing_required_setting`: reject absent and empty required values. |
| S2-005 | Environment Architecture; Environment Identity; Configuration Management | `test_s2_005_invalid_value`: reject invalid environment identity, project/container names, port, host and unsuitable database or role names. |
| S2-006 | Security / Credential and Environment Identity Protection | `test_s2_006_password_file_validation`: reject missing files and insecure permissions for both password files. |
| S2-007 | Data Architecture / Credential Management | `test_s2_007_password_files_separate`: reject the same password file, including hard-link aliases. |
| S2-008 | Data Architecture / Data Storage and Persistence | `test_s2_008_storage_location`: reject checkout-contained, checkout-containing and non-directory storage locations, including storage in another checkout. |
| S2-009 | Data Architecture / Credential Management | `test_s2_009_default_pgpass`: resolve the default client password file when `PGPASSFILE` is omitted. |
| S2-010 | Technology; Testing and Acceptance | `test_s2_010_driver_import`: import the pinned Psycopg version and verify its binary implementation. |
| S2-011 | Data Architecture / Configuration Management | `test_s2_011_example_contract`: verify the shared template matches the configuration keys and contains no environment-specific values. |
| S2-039 | Credential Management; Security | `test_s2_039_credential_file_safety`: reject empty password files or files inside another repository checkout. |

Driver installation on the pinned macOS runtime requires running the bootstrap
and dependency check.

### Environment management

The following unit cases in `tests/unit/test_provisioning.py` use test doubles
and temporary storage. They exercise control flow, target validation, and error
handling without contacting Docker or PostgreSQL. Real infrastructure and
PostgreSQL behavior are verified separately in the integration suite.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S2-012 | Environment Provisioning; Data Storage and Persistence | `test_s2_012_reject_conflicting_container`: accept matching inspection data; reject image, project, port, mount, database, role, health-check and credential configuration conflicts without exposing password values. |
| S2-013 | Environment Provisioning; Data Storage and Persistence | `test_s2_013_reject_unrelated_infrastructure`: reject shared/overlapping storage and unexpected containers in the designated project. |
| S2-014 | Environment Architecture | `test_s2_014_independent_targets`: recognize the designated instance alongside independent infrastructure. |
| S2-015 | Environment Provisioning | `test_s2_015_readiness_failure`: reject missing, stopped, unhealthy, starting or incorrectly mapped containers. |
| S2-016 | Environment Provisioning | `test_s2_016_check_read_only`: perform identity verification in a read-only transaction without creating storage or invoking provisioning. |
| S2-017 | Environment Identity; Environment Provisioning | `test_s2_017_first_provisioning`: create missing storage and its parents or reuse an existing empty directory without replacing it; establish identity only when provisioning previously empty storage with no existing container. |
| S2-018 | Environment Identity | `test_s2_018_existing_storage_never_relabels`: fail on missing identity in existing storage without creating a replacement identity. |
| S2-019 | Data Storage and Persistence | `test_s2_019_reject_unknown_storage`: reject nonempty storage without the expected cluster marker before starting infrastructure. |
| S2-020 | Environment Identity | `test_s2_020_invalid_identity_rows`: reject missing, non-singleton or invalid identity records. |
| S2-021 | Environment Identity; Security | `test_s2_021_invalid_identity_structure`: reject missing or invalid relation/protection metadata. |
| S2-022 | Environment Identity | `test_s2_022_identity_mismatch`: reject development and production identities when staging is expected. |
| S2-023 | Environment Provisioning; Technology | `test_s2_023_connected_target_verification`: verify database, role, internal port, PostgreSQL version, superuser status and container address. |
| S2-024 | Environment Identity; TESTING.md Section 5 | `test_s2_024_guard_fails_closed`: reject unsafe configuration, target connection or identity before exposing a database connection to a test. |
| S2-025 | Environment Identity; TESTING.md Section 5 | `test_s2_025_guard_accepts_verified_staging`: yield a connection only after staging verification in a read-only transaction. |
| S2-026 | Credential Management; Security | `test_s2_026_reject_implicit_connection_overrides`: reject inherited libpq overrides without displaying their values. |
| S2-031 | Environment Architecture | `test_s2_031_reject_nonlocal_docker`: reject a remote Docker endpoint. |
| S2-032 | Environment Provisioning; Configuration Management | `test_s2_032_compose_preserves_infrastructure`: use explicit configuration and non-recreating, targeted Compose startup; do not inherit alternate Compose settings or passwords. |
| S2-033 | Environment Provisioning | `test_s2_033_ready_setup_does_not_restart`: verify a running healthy instance without restarting or relabeling it. |
| S2-034 | Environment Provisioning | `test_s2_034_port_conflict_prevents_provisioning`: reject an unavailable host port before creating storage or starting Compose. |
| S2-035 | Environment Identity | `test_s2_035_identity_creation_transaction`: create, seed, protect and verify identity within one transaction; parameterize the identity value. |
| S2-036 | Security; Environment Provisioning | `test_s2_036_docker_failure_does_not_disclose_output`: report actionable provisioning failure without exposing raw Docker output. |
| S2-037 | Environment Architecture | `test_s2_037_other_container_port_conflict`: reject another container's conflicting TCP host port. |
| S2-038 | Environment Provisioning; Environment Identity | `test_s2_038_reuse_stopped_container`: start existing infrastructure without creating a new identity. |
| S2-040 | Credential Management; Security | `test_s2_040_explicit_password_file_authentication`: use explicit libpq target and password-file SCRAM settings; sanitize authentication failures. |
| S2-041 | Environment Provisioning | `test_s2_041_management_entry_point`: dispatch setup/check with the validated local settings and report success. |
| S2-042 | Data Architecture / Credential Management | `test_s2_042_client_credential_selection`: resolve the first matching libpq entry, including comments, wildcards and escaping, without changing the password file. |
| S2-043 | Environment Provisioning; Credential Management | `test_s2_043_missing_client_credential_prevents_setup`: reject missing, empty or invalid matching client credentials at the database provisioning step, before starting Docker or changing database storage; do not disclose or modify credentials. |
| S2-044 | Environment Provisioning; Credential Management | `test_s2_044_invalid_initial_password_prevents_setup`: reject an invalid or mismatched initial password at the database provisioning step before starting infrastructure; preserve credentials and do not initialize storage. |
| S2-045 | Environment Identity; Credential Management | `test_s2_045_existing_cluster_uses_current_client_credential`: reuse running or stopped infrastructure or recreate a removed container against existing storage without requiring the original provisioning password to match the current client credential; verify identity without relabeling. |
| S2-046 | Technology; Environment Provisioning | `test_s2_046_missing_driver_prevents_setup`: reject a missing driver at the database provisioning step before Docker startup or database initialization. |
| S2-047 | Credential Management | `test_s2_047_escaped_matching_initial_credentials`: accept matching passwords with escaped colon and backslash in the client password file without modifying either file. |
| S2-048 | Environment Provisioning; Data Architecture / Credential Management | `test_s2_048_setup_prepares_directories_before_missing_credentials`: create missing storage and protected credential-parent directories, report all missing credential paths, never create credential files or start a container, and reuse directories and existing credentials unchanged on rerun. |
| S2-049 | Environment Provisioning; Data Architecture / Data Storage and Persistence | `test_s2_049_directory_preparation_safety`: do not create directories during a read-only check, with an unsafe credential path or when infrastructure conflicts. |
| S2-050 | Environment Provisioning; Data Architecture / Data Storage and Persistence | `test_s2_050_prepare_rejects_unrelated_mount`: reject creation of credential directories overlapping an unrelated container's bind mount; do not create storage. |

### Environment integration

Before running integration tests, the operator provisions the independent
staging environment with `scripts/manage_environment.py setup` and verifies
it with `check`. Record the initial provisioning and authentication evidence
for both development and staging. Initial provisioning is an operator action;
the test suite never initializes an unidentified database to bypass its safety
guard. Unit tests exercise the initial provisioning branch independently.

The following tests are in `tests/integration/test_environment_management.py`.
The shared autouse guard verifies the designated staging target before the
suite's tests, and guarded connections reverify identity before database
operations and cleanup. Tests fail closed if staging is unavailable.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S2-027 | Environment Provisioning; Credential Management | `test_s2_027_staging_connectivity_and_safe_rerun`: authenticate through the configured password file; check and rerun setup without replacing/restarting the healthy container or altering stored identity or cluster identity. |
| S2-028 | Environment Identity; Security | `test_s2_028_identity_immutable`: reject insertion, update, deletion and truncation of the identity record; roll back attempted changes. |
| S2-029 | Security / Credential and Environment Identity Protection | `test_s2_029_ordinary_role_cannot_access_identity`: reject ordinary-role reads, writes and schema removal; roll back temporary role creation. |
| S2-030 | Data Storage and Persistence; Testing and Acceptance | `test_s2_030_container_recreation_preserves_storage`: after staging verification, stop/remove only its container and recreate with the same settings; verify cluster identity, marker data, role, environment identity, connectivity and unchanged unrelated containers; clean up only guarded test fixtures. |

Execute the integration suite in the staging checkout at the selected Git
revision. The following application database foundation cases extend that suite.

### Application database foundation: unit tests

Cases in `tests/unit/test_initialization.py` use temporary configuration files,
subprocess argument checks, and simulated transactions, without connecting to
PostgreSQL.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S2-051 | Initialization / Execution sequence; Reruns and failures | `test_s2_051_dry_run_read_only`: inspect pending and existing steps in a read-only transaction, with no changes. |
| S2-052 | Initialization / Execution sequence | `test_s2_052_late_conflict_prevents_writes`: a conflict in a later step prevents any apply operation. |
| S2-053 | Initialization / Reruns and failures | `test_s2_053_step_failure_rolls_back_and_stops`: failed step rolls back, earlier commits remain, later steps are not attempted. |
| S2-054 | Initialization / Reruns and failures | `test_s2_054_apply_rerun_reuses_existing_objects`: apply only missing steps; rerun does not repeat completed steps. |
| S2-055 | Initialization / Execution sequence | `test_s2_055_workflow_guards`: reject empty or duplicate steps, concurrent apply, or a non-idle/non-autocommit connection. |
| S2-056 | Initialization (Phase 1) | `test_s2_056_command_arguments_no_connection`: help, incompatible flags, unknown arguments and abbreviated flags are handled without connecting. |
| S2-057 | Initialization / Prerequisites and configuration; Configuration Management | `test_s2_057_connection_settings`: use explicit process settings or local configuration, preserve credentials and avoid creating data directories. |
| S2-058 | Initialization / Prerequisites and configuration; Security | `test_s2_058_reject_unsafe_configuration`: reject missing settings, inappropriate role or database, unsafe overrides and credential files, and conflicting local settings without disclosing credentials. |
| S2-059 | Initialization / Execution sequence | `test_s2_059_migration_manifest_and_seed_mapping`: verify ordered migration files and the exact seven functional descriptions in the seed manifest. |
| S2-068 | Initialization / Prerequisites and configuration; Security | `test_s2_068_connection_prerequisites`: verify connection options and read-only checks of the selected database, role, PostgreSQL version, superuser status and primary status; reject mismatches before yielding the connection. |

### Application database foundation: integration tests

Cases in `tests/integration/test_db_initialization.py` run only against the
verified staging PostgreSQL instance. The fixture resets known application
objects and roles, with restrictive drops in a transaction and guarded cleanup.
Environment identity and persistent storage are not reset. These tests verify
the Stage 2 foundation; full resource API initialization and lifecycle policy
tests remain subject to Stage 3.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S2-060 | Initialization (Phase 1); Environment Identity | `test_s2_060_clean_initialization_and_dry_run`: both dry-run invocations leave catalogs and identity unchanged; apply creates the expected schemas, roles, tables and seven seed records; rerun preserves object identifiers. |
| S2-061 | Initialization / Reruns and failures | `test_s2_061_seed_reconciliation_preserves_metadata`: restore a missing seed without replacing existing seed descriptions or custom types. |
| S2-062 | `arkkan` Schema / Database integrity; Testing and Acceptance | `test_s2_062_schema_constraints`: enforce unique identifiers, foreign keys, required fields, nonblank identifiers, valid states and the single-default index; generate UUIDs and timestamps, preserve opaque identifiers and empty content. |
| S2-063 | `arkkan` Schema / Database integrity; Testing and Acceptance | `test_s2_063_immutability_and_editable_fields`: reject changes to primary keys and every immutable field; permit editing specified mutable metadata. |
| S2-064 | Security; Initialization / Reruns and failures | `test_s2_064_application_roles_have_no_direct_access`: verify login roles have no elevated attributes, direct table privileges or helper execution access; reject unauthorized data and schema operations. |
| S2-065 | Initialization / Execution sequence | `test_s2_065_conflict_before_any_apply`: unexpected later-schema objects prevent all application writes, including earlier role creation. |
| S2-066 | Initialization / Execution sequence; Database integrity; Security | `test_s2_066_existing_definition_conflicts`: reject conflicting catalog definitions, disabled triggers, grants, role attributes and system flags without silently repairing them. |
| S2-067 | Initialization / Reruns and failures | `test_s2_067_actual_step_rollback`: inject a failure after DDL, verify actual rollback of the failed step and retention of the earlier committed step; later steps remain unapplied. |

Run `tests/unit` in both checkouts and `tests/integration` in staging before
Stage 2 acceptance. Record actual execution outcomes in the stage execution
report. Collection or a simulated transaction is not evidence that PostgreSQL
integration tests passed.

### Manual local-development backup and restore

The Technical Requirements, Data Architecture / Backup and Recovery, also
require a documented basic manual procedure. See [Development Guide](DEVELOPMENT.md#manual-development-database-backup-and-restore).
As a closeout verification, verify a successful custom-format
backup, a restore into a new recovery database, matching identity and data,
and unchanged active development environment. This is an operator verification,
not an additional pytest case. Record actual execution status separately from
the automated suite. Container recreation does not establish recovery success.


## Phase 1, Stage 3: PostgreSQL API

The complete inventory is 37 migrations. Work-package counts below describe
their cumulative implementation checkpoints. Actual outcomes, the tested
revision and acceptance status are recorded in the
[Stage 3 execution report](TEST_EXECUTION_PHASE1_STAGE3.md).

### Work Package 1: API foundation

The Stage 2 initialization regressions remain applicable. WP1 introduced
migrations 013–016. The migration manifest, clean initialization, dry run and
rerun checks cover the current cumulative migration set, including subsequent
work packages. Historical Stage 2 execution reports retain the results for
the original 12-step implementation.

The following new integration cases are in `tests/integration/test_db_initialization.py`.
They require the same staging guard and restrictive cleanup as the Stage 2 cases.
The new unit case is in `tests/unit/test_initialization.py`.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S3-001 | API / Common API Contracts: Response JSON | `test_s3_001_response_contract`: success preserves object and array payloads, empty content and optional JSON null values; error includes only the prescribed fields. |
| S3-002 | API / Common API Contracts; Coding Conventions / PostgreSQL Coding Conventions | `test_s3_002_invalid_response_arguments`: reject invalid internal response combinations with SQLSTATE 22023 and a fixed diagnostic that excludes supplied sensitive values. |
| S3-003 | API / Common API Contracts: Shared validation; Read Operations | `test_s3_003_shared_validation`: recognize nonblank literal identifiers, the four lifecycle states and three retrieval modes; reject null and invalid values without normalization. |
| S3-004 | Security / internal function execution restrictions | `test_s3_004_private_helpers_denied`: both application roles lack execute permission for each private helper, including when temporary schema usage is granted inside a rolled-back transaction. |
| S3-005 | Initialization / Execution sequence; Security | `test_s3_005_helper_conflict`: reject a changed security mode, unexpected execute grant or conflicting overload in check and apply mode. |
| S3-006 | Initialization / Execution sequence; Security | `test_s3_006_helper_catalog_check`: simulated catalog results distinguish absent, compliant and conflicting helpers, including body, signature, owner, security mode, ACL and overload mismatches. |
| S3-007 | Initialization / Reruns and failures; Data Lifecycle | `test_s3_007_upgrade_preserves_stage2_database`: initialize the Stage 2 foundation, populate test records, dry-run and apply the pending API migrations, verify existing object identifiers and data remain intact, and verify an idempotent rerun. |

These tests do not establish the public operation contracts, lifecycle policy,
concurrency behavior or public API authorization. Those tests appear in the
following work packages. Public API tests verify the exact operation
name, response fields and operation-specific data or error behavior.


### Work Package 2: Resource and type writes

Migrations 017–021 add the five specified write operations. The cumulative
initialization inventory at WP2 is 21 migrations. That checkpoint keeps function
and schema access restricted to the deployment owner; WP5 adds runtime grants.
Tests use temporary grants inside rolled-back transactions to verify definer
execution without giving runtime roles table or internal-helper access.

The unit case is in `tests/unit/test_initialization.py`; the integration cases
are in `tests/integration/test_db_initialization.py`. All database cases retain
the staging guard, isolated setup and restrictive cleanup. Execution outcomes
are recorded separately in the Stage 3 execution report. Collection is not a pass.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S3-008 | Initialization / Execution sequence; Security | `test_s3_008_write_function_catalog_check`: simulated catalogs distinguish absent, compliant and conflicting definitions for each write function, including signatures, argument names/defaults, body, owner, language, security mode, volatility, search path, return type, ACL and overloads. |
| S3-009 | Admin API / resource-type operations | `test_s3_009_type_write_contracts`: create a custom type with generated UUID and false system flag, preserve literal slugs, update custom and protected descriptions including empty and null values, and delete an unused custom type; verify response payloads and persisted values. |
| S3-010 | Shared validation; Resource Types; type deletion restrictions | `test_s3_010_invalid_type_writes_preserve_data`: reject blank/null slugs, duplicate creation, missing targets and deletion of each protected type without changing data. |
| S3-011 | Admin API / delete_resource_type; referential integrity | `test_s3_011_referenced_type_deletion_denied`: reject deletion of a type referenced by a resource with versions or with no versions. |
| S3-012 | Admin API / add_resource; Resource Metadata; Resource Versions | `test_s3_012_add_resource_contract`: verify generated IDs, exact slugs, opaque versions, UTC timestamp under a non-UTC session timezone, empty content/default state, optional fields, existing metadata preservation, omitted type for existing resources and atomic default replacement. |
| S3-013 | Shared validation; add_resource; lifecycle rules | `test_s3_013_invalid_add_resource_preserves_data`: reject invalid identifiers, missing/unknown/mismatched types, duplicate versions, null content and disallowed initial states; preserve all data and exclude supplied content from errors. |
| S3-014 | Common API Contracts / transactional mutations; add_resource | `test_s3_014_add_resource_rolls_back_after_write`: inject a unique-constraint failure after definition creation or default demotion; verify all preceding changes roll back and errors exclude raw diagnostics and content. |
| S3-015 | Admin API / update_resource; immutability | `test_s3_015_update_resource_contract`: verify mixed and individual metadata updates, omitted-field preservation, empty strings versus null clearing, exact updated-field payloads, unchanged immutable fields, version-information updates across all lifecycle states and metadata updates on an empty resource. |
| S3-016 | Shared validation; update_resource | `test_s3_016_invalid_updates_are_atomic`: reject null/non-object/empty changes, unknown or immutable keys, non-string/non-null values, invalid identifiers, invalid version combinations and missing targets; mixed invalid updates leave every row unchanged. |
| S3-017 | Security; API boundaries; intermediate checkpoint safety | `test_s3_017_write_functions_restricted`: both runtime roles lack WP2 execution privileges, even with temporary schema usage; temporary admin grants permit all five operations through SECURITY DEFINER without direct table/helper grants. Permanent role authorization is validated in WP5. |
| S3-018 | Initialization / conflicting-object failures; Security | `test_s3_018_write_function_conflict`: check and apply reject changed security mode/search path, PUBLIC execute grants and conflicting overloads without replacing existing objects. |
| S3-019 | Initialization / idempotency; data preservation | `test_s3_019_upgrade_preserves_wp1`: initialize WP1, retain populated records and existing object identifiers through read-only planning and upgrade to the complete migration set, and verify an unchanged rerun. |
| S3-020 | Common API Contracts / concurrency and atomicity | `test_s3_020_concurrent_writes`: concurrent new/existing default creation keeps exactly one default; duplicate versions and competing immutable types produce one success; type deletion and resource creation cannot create an orphan; disjoint metadata updates both survive. |
| S3-021 | Common API Contracts / serialized resource writes | `test_s3_021_resource_writes_wait_for_lock`: hold a resource row lock and observe every resource mutation, including cleanup, blocked by that backend before releasing the lock and verifying success; avoids relying only on simultaneous thread scheduling. |

The shared WP2 call helper checks exact operation names, response keys, result
values and operation-specific object/array payloads or nonblank error reasons
for every completed call.
Catalog unit checks do not establish PostgreSQL syntax, catalog representation,
locking behavior or database acceptance. Required staging execution covers the
entire applicable suite, including the earlier-stage regressions.


### Work Package 3: Read operations

Migrations 022–027 implement four read operations, including three explicit
`get_resource_content` signatures. Omitted version selects the default;
explicit null/blank version is rejected. All read functions use a single
statement snapshot and return content only through `get_resource_content`.
The following integration tests use the staging guard. The cumulative migration
inventory at WP3 is 27.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S3-022 | Read Operations / get_resource_content; default lookup | `test_s3_022_content_selection_matrix`: exercise all retrieval modes and call forms against missing, disabled, obsolete, enabled and default versions, with and without a fallback default; verify selected version/state/content and successful empty content. |
| S3-023 | Read Operations; Shared validation | `test_s3_023_read_metadata_and_validation`: metadata includes every lifecycle state and empty resources without content, lists include versionless resources, timestamps use UTC, unknown targets and invalid identifiers/modes return errors. |


### Work Package 4: Deletion and lifecycle

Migrations 028–036 add private transition/bulk-state helpers and the seven
lifecycle operations. Resource mutations lock the parent definition; cleanup
locks parents in UUID order. Bulk selection membership is captured before
changing defaults. The cumulative inventory at WP4 is 36 migrations.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S3-024 | Resource States; set_resource_state | `test_s3_024_state_transition_matrix`: cover all 16 source/target pairs with force both false and true, default replacement and invalid inputs; rejected operations preserve all rows. |
| S3-025 | Bulk state operations; default policies | `test_s3_025_bulk_state_policy`: reject partial-invalid, same-state, default-removal and multiple-default outcomes; preserve selected membership during promotion; cover successful bulk transitions, zero matches, empty resources and invalid states/targets. |
| S3-026 | Admin API / Delete Operations | `test_s3_026_deletion_contracts`: single, resource-wide and global obsolete deletion preserve definitions; explicit deletion accepts empty/all-obsolete resources and rejects active versions; counts, missing/invalid targets and retained types match contracts. |
| S3-027 | Common API Contracts / rollback | `test_s3_027_mutation_failure_rolls_back`: injected serialization failures after mutation roll back explicit deletion, cleanup and bulk state changes without leaking diagnostics. |


### Work Package 5: Access grants and complete initialization

Migration 037 grants CONNECT on the selected database, USAGE on `arkkan_api`,
all public functions to administrators, and only read functions to users.
Catalog checks reject excess or grantable privileges; missing authorized grants
are pending work. The cumulative inventory is 37 migrations and 18 public SQL
signatures for the 16 operations. S3-017 explicitly initializes the WP2 subset
to retain verification of that intermediate checkpoint. S3-004 also covers
both private state helpers.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S3-028 | Security; Common API Contracts / Authorization | `test_s3_028_final_role_permissions`: verify and exercise every signature under both roles, successful read call forms, denial of user writes, schema creation and direct table access. |
| S3-029 | Initialization / idempotency and rollback | `test_s3_029_access_reconciliation_and_rollback`: a failure after grant SQL rolls back the entire step; partial/missing authorized grants reconcile without changing resource data or edited seed descriptions; reruns apply no changes. |
| S3-030 | Security; Initialization / conflict rejection | `test_s3_030_excess_access_rejected`: reject user writes, PUBLIC execution, grant options, schema creation, internal schema usage and private-helper execution in both check/apply modes. |
| S3-031 | Initialization / planning access grants | `test_s3_031_access_readiness` in `tests/unit/test_initialization.py`: missing roles, database/schema privileges or required function permissions prevent reporting access ready; the complete simulated contract succeeds. |
| S3-032 | Resource States; concurrency | `test_s3_032_concurrent_default_promotions`: competing promotions through `set_resource_state` serialize, both succeed, preserve all versions and leave exactly one default. |

## Phase 1, Stage 4: Python API

The 35 identifiers below cover 320 Stage 4 unit cases and six integration cases.
Together with earlier stages, the cumulative inventory is 592 unit and 85
integration cases. Actual results, tested revisions and limitations are in the
[Stage 4 execution report](TEST_EXECUTION_PHASE1_STAGE4.md); definitions here do
not themselves establish a pass.

### Work Package 1: Execution foundation

These cases are in `tests/unit/test_api.py`. Driver doubles isolate the Python
execution boundary; no PostgreSQL connection is opened. Public wrappers and
actual PostgreSQL integration are covered by subsequent packages. Stage 4 acceptance still
requires all operation/error integration cases and prior-stage regression tests.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S4-001 | Python Interface; Security | `test_s4_001_parameterized_call`: schema-qualified SQL, bound parameters, exact literal/null/boolean values, explicit transactional connection, commit and cleanup. |
| S4-002 | Common API Contracts / Response JSON | `test_s4_002_decoded_payload`: preserve decoded objects, arrays, empty content, null fields and zero counts. |
| S4-003 | Common API Contracts / transactional mutations | `test_s4_003_sql_rejection_rolls_back`: preserve the SQL error envelope and roll back instead of committing. |
| S4-004 | Data Architecture / Configuration Management | `test_s4_004_configuration_failure`: missing/blank required configuration is rejected before connecting; blank settings exercised here, missing settings in S1-003. |
| S4-005 | Python Interface; Security; error translation | `test_s4_005_safe_failures`: connection, execution, fetch, commit and rollback failures produce safe error envelopes without logging diagnostics or retrying; acquired connections close. |
| S4-006 | Common API Contracts / Response JSON | `test_s4_006_invalid_response`: reject malformed/mismatched envelopes, roll back and close without returning the invalid payload. |
| S4-007 | Python Interface / connection lifecycle | `test_s4_007_unexpected_failure_closes`: interruptions and unexpected programming failures propagate after closing the connection; no commit is attempted. Closing an uncommitted connection abandons its transaction. |
| S4-008 | Data Architecture / runtime configuration | `test_s4_008_configuration_per_call`: reread settings on each call and map environment names to libpq connection options, including the external password-file path. |
| S4-009 | Python Interface / failure cleanup | `test_s4_009_rollback_failure_closes`: rollback failure after SQL rejection or commit failure still closes, exposes no raw diagnostics and does not retry rollback. |

### Work Package 2: Read wrappers

Cases in `tests/unit/test_read.py` exercise the four exported functions with a
double for the shared execution boundary. They verify Python routing and local
validation, not PostgreSQL selection, permissions or transaction behavior.
WP5 covers those database checks; see the Stage 4 execution report for evidence.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S4-010 | Python Interface; Coding Conventions / public exports | `test_s4_010_public_exports`: the four implemented read functions remain exported and documented, with no duplicate exports. S4-017 checks the cumulative WP3 export set. |
| S4-011 | Read Operations; literal identifiers; SQL NULL mapping | `test_s4_011_read_mapping`: positional and named identifiers route to the matching operation unchanged, including Unicode, SQL-like text, blank strings and explicit null for SQL validation. |
| S4-012 | get_resource_content / three call forms and modes | `test_s4_012_content_call_forms`: distinguish omitted version/mode from explicit null; route one, two or three parameters and forward all retrieval modes without implementing selection policy. |
| S4-013 | get_resource_content / call contract | `test_s4_013_mode_requires_version`: mode without version returns a safe error without execution, including explicit null/empty mode. |
| S4-014 | Testing and Acceptance / Python input validation | `test_s4_014_invalid_python_types`: reject booleans, numbers, bytes and containers in identifier/version/mode positions without execution or exposing supplied values. |
| S4-015 | Common API Contracts / decoded response | `test_s4_015_response_passthrough`: preserve success/error envelopes, selected content version, empty content/list, optional null metadata and empty version lists. |
| S4-016 | Testing and Acceptance / malformed calls | `test_s4_016_malformed_call`: missing, excessive, unknown and duplicate Python arguments raise TypeError before execution. |

### Work Package 3: Resource administration wrappers

Cases in `tests/unit/test_write.py` isolate execution with a test double and use
the pinned Psycopg JSONB dumper to verify serialization without a connection.
They establish wrapper behavior, not PostgreSQL business-policy enforcement;
WP5 covers database integration; stage acceptance remains a separate gate.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S4-017 | Python Interface; public exports | `test_s4_017_public_exports`: the nine WP3 operations remain exported with no duplicates and all five administration wrappers are documented; S4-024 checks the complete export set. |
| S4-018 | Admin API / Write Operations; literal values and defaults | `test_s4_018_write_mapping`: route positional/named arguments unchanged; preserve optional nulls, empty content, disabled default, protected-type targets and invalid state values for SQL validation. |
| S4-019 | update_resource; omitted versus null metadata | `test_s4_019_json_changes`: serialize exact JSONB keys/values, distinguish SQL NULL from JSON null fields, preserve empty strings, copy the caller's dictionary, and forward version combinations/unknown keys to SQL without implementing policy. |
| S4-020 | Python input validation; safe errors | `test_s4_020_invalid_changes`: reject non-object changes, non-string keys and non-string/non-null values without execution or disclosure. |
| S4-021 | Python input validation | `test_s4_021_invalid_text_arguments`: reject invalid types in every text argument position, including attempts to pass JSONB adapters directly, without execution. |
| S4-022 | Common API Contracts / Response JSON | `test_s4_022_response_passthrough`: preserve success/error dictionaries unchanged for each administration operation. |
| S4-023 | Testing and Acceptance / malformed calls | `test_s4_023_malformed_call`: missing, excessive, unknown and duplicate Python arguments raise TypeError before execution. |


### Work Package 4: Lifecycle and deletion wrappers

Cases in `tests/unit/test_lifecycle.py` use a double for the execution boundary.
They verify Python contracts only; PostgreSQL policy enforcement, permissions,
transactions and cumulative integration validation are covered by WP5.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S4-024 | Python Interface; public exports | `test_s4_024_complete_exports`: exactly all 16 specified operations are exported, callable and documented. |
| S4-025 | Admin API / Delete and State Operations | `test_s4_025_mapping`: route all seven operations with exact positional/keyword arguments, default false force, literal Unicode/SQL-like text, blanks, nulls and invalid states for SQL validation. |
| S4-026 | set_resource_state / force | `test_s4_026_force_mapping`: preserve explicit false, true and SQL NULL using positional and keyword calls. |
| S4-027 | Python input validation; safe errors | `test_s4_027_invalid_types`: reject booleans and other non-text values in every text position, and non-boolean/non-null force values, without execution or exposing input. |
| S4-028 | Common API Contracts / Response JSON | `test_s4_028_response_passthrough`: preserve success/error envelopes, zero counts and state payloads unchanged for every operation. |
| S4-029 | Python call contracts | `test_s4_029_malformed_calls`: reject excessive/unknown arguments, missing/duplicate required arguments and force on bulk operations with TypeError before execution. |

### Work Package 5: Python/PostgreSQL integration

Cases in `tests/integration/test_python_api.py` run at a committed revision in
verified staging. Each test initializes and resets application objects through
the existing guarded helpers. Temporary admin/reader passwords use a protected
temporary client file; operator credentials remain unchanged. A connection hook
verifies the staging target before opening each real Psycopg connection with the
Python API's runtime options. Queries, authentication, transactions, JSONB
adaptation and responses are real; this hook is a safety guard, not a database double.
Every completed call checks its response envelope and connection closure.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S4-030 | Python Interface; reads and metadata writes | `test_s4_030_write_and_read_contracts`: real admin writes persist, JSONB updates retain empty/null values and caller input; both roles read all content call forms/modes and metadata; Unicode/SQL-like identifiers remain literal. |
| S4-031 | Python Interface; lifecycle/deletion | `test_s4_031_lifecycle_and_deletion`: exercise all seven wrappers, force/default protection, bulk/guarded transitions, deletion counts including zero, retained empty resources and custom-type deletion. |
| S4-032 | Security; error translation | `test_s4_032_reader_cannot_write`: every write operation is denied under the real reader login, returns a safe permission error and preserves application data. |
| S4-033 | Input validation; atomicity | `test_s4_033_invalid_calls_preserve_data`: invalid read/write/lifecycle inputs produce common errors and leave the resource metadata/version state unchanged. |
| S4-034 | Transactions; safe diagnostics | `test_s4_034_failure_rolls_back`: inject a version-insertion failure after resource creation, verify rollback and sanitized diagnostics, remove the trigger and confirm recovery. |
| S4-035 | Connection failures; runtime configuration | `test_s4_035_connection_failure`: deny login to the temporary reader role, verify a safe connection error, restore login and confirm a subsequent database response. |

Run these cases with all earlier unit and integration tests for the cumulative
WP5 gate. The Stage 4 execution report records the cumulative results and
affected-test rerun separately. Owner acceptance is a separate decision.


## Phase 1, Stage 5: CLI

### Work Package 1: Foundation and read commands

`tests/unit/test_cli.py` covers local parsing and presentation using public API
doubles. Database connections are blocked. The installed executable is exercised
from a temporary directory for help only. These 66 cases bring the unit inventory
to 658 at WP1; they do not establish real PostgreSQL CLI behavior. WP2 adds
creation/update, UTF-8 input and clearing cases below. WP3 adds lifecycle and
deletion coverage; real CLI authorization remains for WP4. Actual results are in the
[Stage 5 execution report](TEST_EXECUTION_PHASE1_STAGE5.md).

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S5-001 | CLI / Argument conventions; Output and errors | `test_s5_001_invalid_arguments`: missing/unknown commands, values, invalid mode/combinations and out-of-scope options exit 2 on stderr before any public API call. |
| S5-002 | CLI / help at every command level | `test_s5_002_help`: both help flags succeed at root, group and implemented command levels without connecting. |
| S5-003 | CLI / Command reference; literal tokens and defaults | `test_s5_003_read_mapping`: route four read operations, all content call forms/modes, blank and Unicode/literal arguments unchanged; preserve complete JSON responses. |
| S5-004 | CLI / Output and errors | `test_s5_004_exact_content`: preserve empty, Unicode, whitespace and newline content exactly in human and JSON modes. |
| S5-005 | CLI / human-readable metadata | `test_s5_005_metadata_output`: list, default and info show identifiers/metadata, null/empty fields and empty/populated collections without content. |
| S5-006 | CLI / API errors and exit codes | `test_s5_006_api_error_output`: every read command returns 1 for API errors; human errors use stderr, JSON errors preserve the envelope on stdout. |
| S5-007 | CLI / Installation and database access | `test_s5_007_missing_configuration`: missing runtime settings return the API configuration error and exit 1 before connecting. |
| S5-008 | CLI / installable executable | `test_s5_008_installed_entry_point`: installed executable runs help outside the checkout with libpq variables removed; exits 0 without stderr. |


### Work Package 2: Creation and metadata updates

`tests/unit/test_cli_write.py` adds 145 cases with public API doubles and blocked
database connections. The cumulative unit inventory at WP2 is 803 (211 CLI cases).
Temporary files and binary-backed stdin verify input preservation; these are
local boundary tests, not PostgreSQL write or authorization evidence.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S5-009 | CLI / resource add; literal tokens and defaults | `test_s5_009_add_defaults_and_options`: omitted type/metadata, empty content, disabled default and supplied values route unchanged; state validity remains an API/database concern. |
| S5-010 | CLI / UTF-8 files and standard input | `test_s5_010_utf8_content`: exact empty/Unicode/BOM/CRLF/whitespace content, independent of stdin text encoding; source files and stream ownership preserved. |
| S5-011 | CLI / local input errors | `test_s5_011_content_errors_before_api`: reject invalid UTF-8, missing files, directories and invalid paths before API calls; exit 2, stderr only, no content disclosure, including with `-j`. |
| S5-012 | CLI / resource update and metadata clearing | `test_s5_012_metadata_changes`: all 63 nonempty combinations of omitted/set/empty/clear values produce exact keys and nulls, with version supplied only for version information. |
| S5-013 | CLI / type add and update | `test_s5_013_type_mapping`: literal types and absent/set/empty/cleared descriptions map to their public APIs without normalization. |
| S5-014 | CLI / invalid argument combinations | `test_s5_014_invalid_write_arguments`: reject missing values, no updates, invalid version/info combinations, conflicting setters/clearers, unknown or abbreviated options before any API call. |
| S5-015 | CLI / help | `test_s5_015_write_help`: both help flags work for all four new commands without connecting. |
| S5-016 | CLI / output and errors | `test_s5_016_write_output`: new commands preserve complete JSON responses and API errors; human output includes identifiers/updated fields, correct streams and exit codes. |
| S5-017 | CLI / safe local input failures | `test_s5_017_read_failure_sanitized`: simulated file/stdin permission failures exit 2 before API calls without leaking raw diagnostics. |
| S5-018 | CLI / reject syntax before processing | `test_s5_018_syntax_before_input`: an invalid option rejects a stdin-based creation command without consuming stdin or calling the API. |


### Work Package 3: Lifecycle and deletion commands

`tests/unit/test_cli_lifecycle.py` adds 128 cases with public API doubles and
blocked database connections. The cumulative inventory is 931 unit cases,
including 339 CLI cases. All 16 command mappings now have local coverage;
actual lifecycle policy, persistence and authorization through the executable
remain WP4 validation, not evidence established by these doubles.

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S5-019 | CLI / lifecycle and deletion command mappings; output/errors | `test_s5_019_lifecycle_mapping_and_output`: each of eight new commands calls exactly its public API with the expected arguments; human/JSON success and API errors use the correct streams, identifiers/counts and exit codes. |
| S5-020 | CLI / literal positional and state tokens | `test_s5_020_literal_lifecycle_tokens`: preserve empty, whitespace and Unicode/SQL-like tokens without local business-policy validation. |
| S5-021 | CLI / single-version force | `test_s5_021_force_and_state_policy`: absent/present `-F` maps to false/true for all four states and an invalid state; API rejection is preserved even with force. |
| S5-022 | CLI / successful zero counts | `test_s5_022_zero_counts`: all five count-returning operations display zero and exit successfully. |
| S5-023 | CLI / option scope and syntax rejection | `test_s5_023_invalid_lifecycle_arguments`: missing inputs, irrelevant options and abbreviated help fail before API calls; all 15 operations other than single-version state reject `-F`. |
| S5-024 | CLI / help | `test_s5_024_lifecycle_help`: both help flags work for all eight new commands without connecting; only single-version state advertises `-F`. |

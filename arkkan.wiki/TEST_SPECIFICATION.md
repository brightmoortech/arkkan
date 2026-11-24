# arkkan Test Specification

Test governance is defined in `TESTING.md`. Test cases map to the applicable
sections of `TECHNICAL_REQ.md`. This specification covers only the authorized
implementation scope and expands with subsequent stages.

## Phase 1, Stage 1: Project Foundation

| ID | Requirement / acceptance criterion | Test and expected outcome |
|---|---|---|
| S1-001 | Phase 1 Implementation Strategy: package installs in a clean environment | `tests/unit/test_import.py::test_s1_001_package_import`: package imports; no premature public API exports. Run after clean bootstrap for installation evidence. |
| S1-002 | Initialization / Prerequisites and configuration; CLI / Installation and database access | `test_s1_002_required_settings`: valid PGDATABASE and PGUSER are accepted. |
| S1-003 | Same configuration requirements; Stage 1 configuration validation | `test_s1_003_required_validation`: each required setting is rejected when missing, empty or whitespace-only; error identifies the variable. |
| S1-004 | Initialization / Prerequisites and configuration; CLI / Installation and database access | `test_s1_004_optional_settings`: optional PGHOST, PGPORT and PGPASSFILE are preserved; omitted settings are not added (also covered by S1-002). Actual libpq default resolution is not tested at Stage 1. |
| S1-005 | Security; Cross-Phase Requirements | `test_s1_005_preserve_values_and_exclude_credentials`: identifiers are preserved and unrelated variables and passwords are not returned. |
| S1-006 | Cross-Phase Requirements: externally configurable connections | `test_s1_006_process_environment`: configuration reads the process environment by default. |

Configuration tests are in `tests/unit/test_config.py`. They do not open a database connection or read password files. PostgreSQL connection and password-file behavior are covered when the relevant initialization and CLI stages are implemented.

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
revision. Application schema, seed data and initialization tests are still
required in the following work package. In particular, testing application
schema resets without affecting environment identity requires the application
schema and is deferred until that work package. This is not the complete Stage
2 test suite.

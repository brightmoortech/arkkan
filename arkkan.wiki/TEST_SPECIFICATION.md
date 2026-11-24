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
| S2-004 | Environment Provisioning / Configuration Management | `test_s2_004_missing_required_setting`: reject absent and empty required values. |
| S2-005 | Environment Architecture; Environment Identity; Configuration Management | `test_s2_005_invalid_value`: reject invalid environment identity, project/container names, port, host and unsuitable database or role names. |
| S2-006 | Security / Credential and Environment Identity Protection | `test_s2_006_password_file_validation`: reject missing files and insecure permissions for both password files. |
| S2-007 | Data Architecture / Credential Management | `test_s2_007_password_files_separate`: reject the same password file, including hard-link aliases. |
| S2-008 | Data Architecture / Data Storage and Persistence | `test_s2_008_storage_location`: reject checkout-contained, checkout-containing and non-directory storage locations, including storage in another checkout. |
| S2-009 | Data Architecture / Credential Management | `test_s2_009_default_pgpass`: resolve the default client password file when `PGPASSFILE` is omitted. |
| S2-010 | Technology; Stage 2 environment tests and validation | `test_s2_010_driver_import`: import the pinned Psycopg version and verify its binary implementation. |
| S2-011 | Data Architecture / Configuration Management | `test_s2_011_example_contract`: verify the shared template matches the configuration keys and contains no environment-specific values. |

Driver installation on the pinned macOS runtime requires running the bootstrap
and dependency check. Actual Compose provisioning, driver connectivity and
password-file authentication, identity enforcement, external storage persistence,
and database foundation tests remain to be implemented and validated in the
subsequent Stage 2 work packages. This is not the complete Stage 2 test suite.

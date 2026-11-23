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

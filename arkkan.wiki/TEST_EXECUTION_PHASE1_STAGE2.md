# arkkan Test Execution Report

## Phase 1, Stage 2: Database Foundation

- Closeout review date: 2026-11-24.
- Validated implementation checkpoint: `83ffc53c6fe1fcad8b06c982086b47865a823e86` (`main`; staging detached at this revision).
- Validation environment: macOS, Python 3.12.10, pytest 9.1.1; PostgreSQL image `postgres:18.7-bookworm`; Psycopg binary 3.3.9 (pinned configuration).
- Evidence: project-owner terminal output and explicit aggregate test confirmations; source and tracked Git baseline inspected during closeout. Not independently executed on the reviewer's machine.
- Governing documents: `TECHNICAL_REQ.md`, `FUNCTIONAL_REQ.md`, `TESTING.md`, `TEST_SPECIFICATION.md`.
- Status: automated validation and the same-cluster backup/restore drill passed as reported; post-drill environment checks, documentation checkpoint and formal owner acceptance pending.
- Roadmap context: `TECHNICAL_REQ.md`, Development & Deployment / Roadmap and Phase 1 Implementation Strategy.

## 1. Implementation and checkpoint

WP1 environment foundation (`ae422e1`), WP2 environment management (`8898534`),
WP3 application database foundation (`83ffc53`). WP2 documentation checkpoint
`402179d292ac1ee54bf284c97496931dc66509e4` precedes WP3. WP4 is the closeout
review and documentation reconciliation; no new application feature is introduced.
The owner reported successful push, staging fetch and exact detached checkout;
`git status --short` displayed no changes and `git rev-parse HEAD` returned the
full validated revision in both checkouts. The uploaded tracked files match that
revision. The documentation closeout commit is separate and remains pending.

## 2. Actual execution evidence

Earlier Stage 2 work packages: development/staging provisioning and environment
checks succeeded as reported; development safe setup rerun succeeded. WP2 unit
suite: 156 passed independently in each checkout; staging environment integration
suite: 7 passed as reported. These are earlier regression milestones, not additive
final test totals. Full earlier terminal logs and exact run dates are not retained
in the available closeout evidence.

WP3/final automated suite, reported during Stage 2 closeout:

| Checkout | Command | Reported result | Evidence |
|---|---|---|---|
| Development | `.venv/bin/python scripts/init_db.py` | 12 pending; read-only dry run successful | Terminal output |
| Development | `.venv/bin/python -m pytest tests/unit` | 188 passed before apply | Owner confirmation |
| Development | `.venv/bin/python scripts/init_db.py --apply` | 12 applied | Terminal output |
| Development | `.venv/bin/python -m pytest tests/unit` | 188 passed in 0.60 s after apply | Terminal output, Darwin/Python 3.12.10/pytest 9.1.1 |
| Development | `.venv/bin/python scripts/init_db.py` | 12 unchanged; no writes reported | Terminal output |
| Development | `.venv/bin/python scripts/init_db.py --apply` | 12 unchanged; 0 applied | Terminal output |
| Staging | `.venv/bin/python -m pytest tests/unit` | All 188 passed | Owner confirmation of expected suite |
| Staging | `.venv/bin/python -m pytest tests/integration -v` | 21 passed | Owner aggregate confirmation |

The final staging aggregate represents seven infrastructure cases and fourteen
application database initialization cases. The full per-case staging transcript
and durations were not provided. Per-ID outcomes below are mapped from the
reported all-passed suites and the source/test specification, not independent
per-case terminal observations. No failures, skips or blocked automated cases
were reported. The latest development unit output explicitly reports only passes.

## 3. Test case traceability and results

74 unique test function identifiers cover the current and prior stage. A
separate source-only `pytest --collect-only -q tests/unit tests/integration`
check during closeout confirmed 188 unit and 21 integration cases, including
parameterized expansions. This check establishes inventory, not execution.
The Stage 1 regression cases remain included in unit testing.

| Test ID | Suite | Test function | Expanded cases | Outcome |
|---|---|---|---:|---|
| S1-001 | unit | `test_s1_001_package_import` | 1 | Passed (reported suite) |
| S1-002 | unit | `test_s1_002_required_settings` | 1 | Passed (reported suite) |
| S1-003 | unit | `test_s1_003_required_validation` | 6 | Passed (reported suite) |
| S1-004 | unit | `test_s1_004_optional_settings` | 1 | Passed (reported suite) |
| S1-005 | unit | `test_s1_005_preserve_values_and_exclude_credentials` | 1 | Passed (reported suite) |
| S1-006 | unit | `test_s1_006_process_environment` | 1 | Passed (reported suite) |
| S2-001 | unit | `test_s2_001_literal_configuration` | 1 | Passed (reported suite) |
| S2-002 | unit | `test_s2_002_reject_invalid_configuration` | 7 | Passed (reported suite) |
| S2-003 | unit | `test_s2_003_valid_contract_does_not_write` | 1 | Passed (reported suite) |
| S2-004 | unit | `test_s2_004_missing_required_setting` | 18 | Passed (reported suite) |
| S2-005 | unit | `test_s2_005_invalid_value` | 11 | Passed (reported suite) |
| S2-006 | unit | `test_s2_006_password_file_validation` | 2 | Passed (reported suite) |
| S2-007 | unit | `test_s2_007_password_files_separate` | 2 | Passed (reported suite) |
| S2-008 | unit | `test_s2_008_storage_location` | 4 | Passed (reported suite) |
| S2-009 | unit | `test_s2_009_default_pgpass` | 1 | Passed (reported suite) |
| S2-010 | unit | `test_s2_010_driver_import` | 1 | Passed (reported suite) |
| S2-011 | unit | `test_s2_011_example_contract` | 1 | Passed (reported suite) |
| S2-012 | unit | `test_s2_012_reject_conflicting_container` | 10 | Passed (reported suite) |
| S2-013 | unit | `test_s2_013_reject_unrelated_infrastructure` | 4 | Passed (reported suite) |
| S2-014 | unit | `test_s2_014_independent_targets` | 1 | Passed (reported suite) |
| S2-015 | unit | `test_s2_015_readiness_failure` | 5 | Passed (reported suite) |
| S2-016 | unit | `test_s2_016_check_read_only` | 1 | Passed (reported suite) |
| S2-017 | unit | `test_s2_017_first_provisioning` | 2 | Passed (reported suite) |
| S2-018 | unit | `test_s2_018_existing_storage_never_relabels` | 2 | Passed (reported suite) |
| S2-019 | unit | `test_s2_019_reject_unknown_storage` | 1 | Passed (reported suite) |
| S2-020 | unit | `test_s2_020_invalid_identity_rows` | 4 | Passed (reported suite) |
| S2-021 | unit | `test_s2_021_invalid_identity_structure` | 3 | Passed (reported suite) |
| S2-022 | unit | `test_s2_022_identity_mismatch` | 2 | Passed (reported suite) |
| S2-023 | unit | `test_s2_023_connected_target_verification` | 6 | Passed (reported suite) |
| S2-024 | unit | `test_s2_024_guard_fails_closed` | 9 | Passed (reported suite) |
| S2-025 | unit | `test_s2_025_guard_accepts_verified_staging` | 1 | Passed (reported suite) |
| S2-026 | unit | `test_s2_026_reject_implicit_connection_overrides` | 1 | Passed (reported suite) |
| S2-027 | integration | `test_s2_027_staging_connectivity_and_safe_rerun` | 1 | Passed (reported suite) |
| S2-028 | integration | `test_s2_028_identity_immutable` | 4 | Passed (reported suite) |
| S2-029 | integration | `test_s2_029_ordinary_role_cannot_access_identity` | 1 | Passed (reported suite) |
| S2-030 | integration | `test_s2_030_container_recreation_preserves_storage` | 1 | Passed (reported suite) |
| S2-031 | unit | `test_s2_031_reject_nonlocal_docker` | 1 | Passed (reported suite) |
| S2-032 | unit | `test_s2_032_compose_preserves_infrastructure` | 1 | Passed (reported suite) |
| S2-033 | unit | `test_s2_033_ready_setup_does_not_restart` | 1 | Passed (reported suite) |
| S2-034 | unit | `test_s2_034_port_conflict_prevents_provisioning` | 1 | Passed (reported suite) |
| S2-035 | unit | `test_s2_035_identity_creation_transaction` | 1 | Passed (reported suite) |
| S2-036 | unit | `test_s2_036_docker_failure_does_not_disclose_output` | 1 | Passed (reported suite) |
| S2-037 | unit | `test_s2_037_other_container_port_conflict` | 1 | Passed (reported suite) |
| S2-038 | unit | `test_s2_038_reuse_stopped_container` | 1 | Passed (reported suite) |
| S2-039 | unit | `test_s2_039_credential_file_safety` | 4 | Passed (reported suite) |
| S2-040 | unit | `test_s2_040_explicit_password_file_authentication` | 2 | Passed (reported suite) |
| S2-041 | unit | `test_s2_041_management_entry_point` | 2 | Passed (reported suite) |
| S2-042 | unit | `test_s2_042_client_credential_selection` | 7 | Passed (reported suite) |
| S2-043 | unit | `test_s2_043_missing_client_credential_prevents_setup` | 4 | Passed (reported suite) |
| S2-044 | unit | `test_s2_044_invalid_initial_password_prevents_setup` | 4 | Passed (reported suite) |
| S2-045 | unit | `test_s2_045_existing_cluster_uses_current_client_credential` | 4 | Passed (reported suite) |
| S2-046 | unit | `test_s2_046_missing_driver_prevents_setup` | 1 | Passed (reported suite) |
| S2-047 | unit | `test_s2_047_escaped_matching_initial_credentials` | 1 | Passed (reported suite) |
| S2-048 | unit | `test_s2_048_setup_prepares_directories_before_missing_credentials` | 3 | Passed (reported suite) |
| S2-049 | unit | `test_s2_049_directory_preparation_safety` | 3 | Passed (reported suite) |
| S2-050 | unit | `test_s2_050_prepare_rejects_unrelated_mount` | 1 | Passed (reported suite) |
| S2-051 | unit | `test_s2_051_dry_run_read_only` | 1 | Passed (reported suite) |
| S2-052 | unit | `test_s2_052_late_conflict_prevents_writes` | 2 | Passed (reported suite) |
| S2-053 | unit | `test_s2_053_step_failure_rolls_back_and_stops` | 1 | Passed (reported suite) |
| S2-054 | unit | `test_s2_054_apply_rerun_reuses_existing_objects` | 1 | Passed (reported suite) |
| S2-055 | unit | `test_s2_055_workflow_guards` | 5 | Passed (reported suite) |
| S2-056 | unit | `test_s2_056_command_arguments_no_connection` | 5 | Passed (reported suite) |
| S2-057 | unit | `test_s2_057_connection_settings` | 1 | Passed (reported suite) |
| S2-058 | unit | `test_s2_058_reject_unsafe_configuration` | 9 | Passed (reported suite) |
| S2-059 | unit | `test_s2_059_migration_manifest_and_seed_mapping` | 1 | Passed (reported suite) |
| S2-060 | integration | `test_s2_060_clean_initialization_and_dry_run` | 1 | Passed (reported suite) |
| S2-061 | integration | `test_s2_061_seed_reconciliation_preserves_metadata` | 1 | Passed (reported suite) |
| S2-062 | integration | `test_s2_062_schema_constraints` | 1 | Passed (reported suite) |
| S2-063 | integration | `test_s2_063_immutability_and_editable_fields` | 1 | Passed (reported suite) |
| S2-064 | integration | `test_s2_064_application_roles_have_no_direct_access` | 2 | Passed (reported suite) |
| S2-065 | integration | `test_s2_065_conflict_before_any_apply` | 1 | Passed (reported suite) |
| S2-066 | integration | `test_s2_066_existing_definition_conflicts` | 6 | Passed (reported suite) |
| S2-067 | integration | `test_s2_067_actual_step_rollback` | 1 | Passed (reported suite) |
| S2-068 | unit | `test_s2_068_connection_prerequisites` | 6 | Passed (reported suite) |

## 4. Validation gate reconciliation

| Requirement / gate | Evidence and status |
|---|---|
| Isolated infrastructure, credential validation, readiness and safe reruns | Environment unit and staging integration cases; development/staging provisioning and check reported successful. |
| Driver compatibility and real password-file authentication | Pinned binary import case and staging connectivity cases passed as reported. Linux validation remains Phase 2. |
| Persistent storage and environment identity protection | Staging container recreation and identity mutation/access rejection cases passed as reported. |
| Mandatory staging safety and application reset isolation | Guard unit tests and guarded integration suite passed as reported. |
| Roles, schemas, constraints, immutable fields and seed reconciliation | Twelve migrations applied in development; staging database initialization cases passed as reported. |
| Read-only default and explicit check, idempotency, conflict and rollback | Development dry-run/apply reruns and staging tests passed as reported. |
| Manual local database backup and restore | Procedure documented in `DEVELOPMENT.md`; same-cluster recovery drill passed as reported (see Section 5). Post-drill active-environment checks remain pending. Container recreation is not restore evidence. |
| Stage 3 API and grants | Not applicable to Stage 2. Full lifecycle policies, public SQL functions and grants, full initialization acceptance remain Stage 3. |
| Stage audits and checkpoint | Earlier implementation audit-and-correction passes reported for work packages. Closeout reconciled source, traceability and reported results against the stage gate; no code modifications in closeout. Implementation checkpoint verified. Documentation review/delivery and closeout commit are separate. |

## 5. Manual local-development recovery drill

Execution date: 2026-11-24. Source: `arkkan_dev` on `arkkan-db-dev`;
recovery target: `arkkan_recovery_test` on the same PostgreSQL 18.7 instance.
Evidence consists of owner-provided terminal output and confirmations.

| Verification | Reported outcome |
|---|---|
| Environment readiness | Setup and check succeeded after a stopped container was discovered. PostgreSQL logs showed no reported fatal or storage errors; the cause of exit 255 was not established. |
| Custom-format backup | `arkkan_dev_20261124_161003.dump`, approximately 15 KB, mode 600, retained under `~/development/data/arkkan/develop/backups/`. |
| Archive catalog | `pg_restore --list` returned 37 TOC entries, including three schemas, four tables, data, integrity functions, triggers, constraints, index and ACL entries. |
| Isolated restore | New recovery database created; `pg_restore --exit-on-error --verbose` restored archived objects and data without reported errors. |
| Data comparison | All seven resource type records matched (UUID, slug, description, system flag); resource definitions and versions each contained zero rows in both databases; environment identity matched (`development`). |
| Schema comparison | Schema-only dumps compared after filtering randomized restrict/unrestrict markers; owner reported no diff output. |
| Cleanup | Owner executed `dropdb` against `arkkan_recovery_test`; no error was reported. The original backup was retained. |

The drill demonstrated logical backup and restoration of the existing database
within its original cluster. It did not exercise populated resource definitions
or versions, selective recovery, role or credential restoration, or recovery
onto a replacement cluster. The commands used a different recovery database
name and did not include the guide's explicit `template0`, `--single-transaction`
or all client error-handling flags. The schema comparison did not independently
capture both dump exit statuses. The exact documented command sequence is
therefore not claimed as fully executed; the guide retains its pending
validation label until the final checks are recorded. Final active-environment checks
(`manage_environment.py check` and `init_db.py` dry run) remain to be recorded.
Full disaster recovery and operational utilities remain Phase 4 work.

## 6. Acceptance disposition

The reported automated results and same-cluster recovery drill support the
Stage 2 database foundation validation. The required manual backup/restore
documentation is supplied. Record the final active-environment checks and
verify the documentation checkpoint before requesting formal owner acceptance.
No Stage 3 authorization or Stage 2 acceptance is inferred from this report.
If any tested implementation, tests or configuration change, rerun affected
and applicable regression tests before acceptance.

# arkkan Test Execution Report

## Phase 1, Stage 4: Python API

- Execution date: 2026-11-25; documentation closeout: 2026-11-26.
- Status: implementation and validation complete; ready for owner acceptance.
  Owner acceptance is deferred until CLI-based manual validation. The owner
  subsequently authorized Stage 5; that decision adds no Stage 4 test evidence.
- Final tested checkpoint: `7e7d5befb5abcdb7f5175acb93ca5c820f457f1e`.
  Cumulative execution used `b663ad865181c290a480b0212c58633927683461`;
  the final checkpoint changes only rollback-test helper transactions.
- Environment: the owner's macOS host, Python 3.12.10, pytest 9.1.1,
  Psycopg binary 3.3.9, PostgreSQL `18.7-bookworm`, container `arkkan-db-test`,
  database `arkkan_test`, host port 5442. The coding assistant executed the tests
  on this host; these are not owner-reported manual results.
- Authority: [Functional Requirements](FUNCTIONAL_REQ.md),
  [Technical Requirements](TECHNICAL_REQ.md), [Testing Governance](TESTING.md)
  and [Test Specification](TEST_SPECIFICATION.md).

## 1. Delivered scope

| Package | Deliverable | Commit |
|---|---|---|
| WP1 | Shared execution, runtime configuration, response validation, transactions and safe errors | `adfa9d5` |
| WP2 | Four public read wrappers and all content call forms | `dcda13f` |
| WP3 | Five resource/type administration wrappers, including JSONB metadata updates | `7319986` |
| WP4 | Seven lifecycle/deletion wrappers; complete 16-operation export set | `d9c48dd` |
| WP5 | Real Python/PostgreSQL integration, regression and fixture corrections | `79105de`, `b663ad8`, `7e7d5be`; evidence commit `f3c8cc2` |
| WP6 | Final usage guidance, traceability, report, registry and handover | Documentation commit follows tested checkpoint |

The Python package calls the existing PostgreSQL API with bound parameters,
returns decoded common JSON responses and leaves resource policies in SQL.
Each call owns its connection and transaction; errors do not expose raw database
diagnostics. Public operations are exported from `arkkan`; implementation modules
remain internal. No dependency, SQL migration or application configuration change
was needed for WP5 or WP6. The CLI belongs to Stage 5.

## 2. Execution evidence

Commands below ran from `/Users/haitham/development/stage/arkkan` at the indicated
committed, detached revisions unless marked development. Durations are pytest's
terminal summaries; JUnit timing can differ slightly.

| Run | Revision | Actual outcome |
|---|---|---|
| Initial focused Python API integration | `79105de` | 6 setup errors in 96.33 seconds; no test passed |
| Corrected focused Python API integration | `b663ad8` | 6 passed in 354.24 seconds; no failures, errors or skips |
| Cumulative unit and integration suite | `b663ad8` | 670 passed, 1 failed, 6 setup errors in 1587.20 seconds; no skips |
| Development unit rerun after helper transaction correction | `7e7d5be` file contents | 592 passed in 1.11 seconds |
| Unit, environment-management and Python API retest | `7e7d5be` | 605 passed in 465.16 seconds; no failures, errors or skips |
| Post-retest environment verification | `7e7d5be` | Passed; staging checkout clean |

Initial focused command:

```bash
.venv/bin/python -m pytest tests/integration/test_python_api.py -q --junitxml=/private/tmp/arkkan-wp5-focused.xml
```

Corrected focused command:

```bash
.venv/bin/python -m pytest tests/integration/test_python_api.py -q --junitxml=/private/tmp/arkkan-wp5-b663ad8-focused.xml
```

Cumulative command:

```bash
.venv/bin/python -m pytest tests/unit tests/integration -q --junitxml=/private/tmp/arkkan-stage4-b663ad8.xml
```

Development unit command: `.venv/bin/python -m pytest tests/unit -q`.
Supplemental staging command and final environment check:

```bash
.venv/bin/python -m pytest tests/unit tests/integration/test_environment_management.py tests/integration/test_python_api.py -q --junitxml=/private/tmp/arkkan-wp5-7e7d5be-retest.xml
.venv/bin/python scripts/manage_environment.py check
```

The initial setup errors came from unsupported `Path.open(opener=...)` usage;
`b663ad8` corrected it. During cumulative execution, S2-030 removed the verified
staging container, but immediate setup reported host port 5442 unavailable. The
six Python API cases then failed closed at their staging safety guards. A later
`.venv/bin/python scripts/manage_environment.py setup` succeeded. The surviving
test marker and non-login role were verified and removed through guarded,
restrictive cleanup. Storage, environment identity and unrelated infrastructure
were preserved. The port conflict did not recur in the supplemental run; its
underlying cause was not established.

### Cumulative coverage and revision limits

Matching JUnit cases by class and test name confirms **677 distinct cases with
successful execution evidence** across cumulative execution and the supplemental
run. The retest includes 592 unit, 7 environment-management and 6 Python API cases;
it resolves every failed or blocked case and exercises the changed rollback test.
The other 72 integration cases retain their successful evidence from `b663ad8`.
There was no single clean 677-case run at `7e7d5be`; WP6 adds no new database run.
No required Stage 4 or earlier automated case remains without a passing execution.

| Identifiers | Unit cases | Integration cases | Final outcome across runs |
|---|---:|---:|---|
| S1-001–006 | 11 | 0 | Passed |
| S2-001–068 | 177 | 21 | Passed, including S2-030 on retest |
| S3-001–032 | 84 | 58 | Passed |
| S4-001–035 | 320 | 6 | Passed |
| Total: 141 identifiers | 592 | 85 | 677 distinct cases passed |

| Stage 4 validation gate | Passing evidence |
|---|---|
| Parameter binding, decoded envelopes, safe failures and transaction/connection cleanup | S4-001–009; real rollback and connection recovery S4-034–035 |
| Public exports, read routing, omitted/null arguments and all content modes | S4-010–016, S4-024, S4-030 |
| Resource/type writes, JSONB values, defaults and caller-data preservation | S4-017–023, S4-030 |
| Lifecycle/deletion calls, force typing, counts and empty resources | S4-024–031 |
| Reader authorization and unchanged data after invalid operations | S4-032–033; cumulative S3 policy/security cases |
| Prior-stage initialization, role isolation, concurrency and persistence | All S1–S3 cases |

Test definitions map each identifier to its requirement and executable function.
Parameterized cases are counted as pytest reports them; additional assertions
within a case are not counted as extra tests. Unit doubles do not establish real
PostgreSQL behavior. Integration tests use real Psycopg authentication and calls,
with temporary protected credentials and a hook that verifies the staging target
before connecting. Operator credential files are unchanged. Automated database
tests did not run against development. Fixture cleanup means passing staging
tests do not leave a ready-to-use application dataset.

### Supplementary artifacts

JUnit files are temporary and may be removed by host cleanup. This report retains
the durable outcomes and traceability. SHA-256 values verified during closeout:

| File under `/private/tmp/` | SHA-256 |
|---|---|
| `arkkan-wp5-focused.xml` | `9e24c41e164c4195d4519944438c6c7afd47c992bd9b6be2806f75845ce95a63` |
| `arkkan-wp5-b663ad8-focused.xml` | `cf2bfd2bb018146f2f66dbfdfc5813530fbd232047e672ada1ad606cd0f18231` |
| `arkkan-stage4-b663ad8.xml` | `908458f92831bc87c6d0e2d45750428824f7a69d205e386f1b4f7e1ac062ba01` |
| `arkkan-wp5-7e7d5be-retest.xml` | `b72d16dd97595865f39e114a206b057719e84868dbc172df756bf077e037b4c6` |

## 3. Audits and corrections

Package correctness reviews checked the 16 operation contracts, exact argument
routing, defaults, null versus omitted values, safe error envelopes, authorization,
JSONB adaptation, rollback and connection closure. Separate engineering reviews
checked helper reuse, export boundaries, mutable test inputs, fixture cleanup,
maintainability and SQL ownership of business rules. These were separate passes
by the coding assistant, not independent external reviewers.

WP6 consolidates those reviews and audits README, DEVELOPMENT, TEST_SPECIFICATION,
AGENTS, ARKKAN_HANDOVER and this report. Content review checks actual source,
requirements, commands, Git revisions and JUnit evidence. Quality review checks
reader clarity, links, terminology and separation of test outcomes from acceptance.
Historical reports and unrelated requirements formatting are preserved.

Priorities below are closeout assessments, not reconstructed historical labels.

| ID | Priority | Finding | Disposition and evidence |
|---|---|---|---|
| S4-KI-001 | Medium | Redundant rollback could occur after rollback failure. | Corrected in WP1; S4-009 and cumulative unit suite passed. |
| S4-KI-002 | Low | Test input isolation, text-position boolean rejection and export ordering needed strengthening. | Corrected in WP3/WP4; corresponding unit suites and cumulative regression passed. |
| S4-KI-003 | High | Test credential-file creation used an unsupported `Path.open` argument. | Corrected in `b663ad8` using builtin `open` with mode-0600 creation; all six integration cases passed afterward. |
| S4-KI-004 | Medium | The staging guard context could translate the API connection exception under test. | Guard verification now finishes before the actual API connection; S4-035 passed with real login denial and recovery. |
| S4-KI-005 | Medium | Partial rollback-test helper setup could survive a setup failure. | Setup and cleanup grouped in transactions in `7e7d5be`; S4-034 passed on retest. |
| S4-KI-006 | Medium | Port 5442 unavailable immediately after staging container removal. | Operationally recovered; S2-030 and all blocked cases passed on retest. Root cause unknown; retain as a limitation and investigate if recurrent. No provisioning change or guard bypass. |
| S4-KI-007 | Low | Documentation retained pending integration and historical checkout wording. | Reconciled status, traceability, checkpoint references and pickup guidance with actual execution evidence. |

## 4. Acceptance checkpoint and limitations

All six Stage 4 packages are complete. The specified operations and errors have
unit and PostgreSQL integration evidence, including prior-stage regression and
successful affected-test reruns as required by Testing Governance. Stage 4 is
ready for the owner's acceptance, with S4-KI-006 disclosed; no unresolved
application defect was identified. The transient port conflict's root cause is
not claimed fixed. No owner acceptance or Stage 5 authorization is implied.

WP6 is documentation only. Its commit must preserve the tested source, tests,
SQL, dependencies and configuration at `7e7d5be`. Subsequent changes require
applicable verification. No CLI, Linux deployment, production-readiness or new
backup/recovery validation is included. Historical recovery limitations remain
in the Stage 2/3 reports and development guide.

# arkkan Automated Testing Governance

## 1. Purpose and Scope

Define how automated tests are specified, organized, executed, verified, and reported throughout the development of `arkkan`.

`FUNCTIONAL_REQ.md` and `TECHNICAL_REQ.md` define the requirements and stage acceptance criteria. This document governs testing without changing those requirements or expanding the authorized implementation scope.

## 2. Framework and Organization

Use pytest as the standard automated testing framework, including Python, PostgreSQL integration, and CLI tests.

| Directory | Purpose |
|---|---|
| `tests/unit/` | Individual Python functions and components, including local CLI argument handling without a database connection. |
| `tests/integration/` | PostgreSQL schema, initialization, SQL functions, permissions, and Python API interactions. |
| `tests/e2e/` | Complete CLI and application workflows. |

Each suite must be independently executable. Introduce tests progressively according to the authorized implementation stage. Tests that require PostgreSQL must use the isolated test database defined in Section 5.

## 3. Test Specification and Traceability

Maintain a single test specification document. Assign each test case a unique identifier and map it to its applicable requirement or acceptance criterion.

Maintain traceability between the specification and automated tests so that coverage and gaps can be identified. Update the specification as tests are introduced or changed within the authorized scope. Include positive, negative, boundary, security, and failure scenarios where required by the specifications.

## 4. Test Execution

- During development, execute tests relevant to the changes.
- After each audit correction, rerun affected tests.
- Before stage completion, execute all applicable tests from the current and previous stages to detect regressions.
- Develop and initially test on macOS during Phase 1; run all Phase 1 acceptance tests on macOS at Stage 6. In Phase 2, rerun applicable Phase 1 tests inside Docker and verify deployment initialization, restart behavior, and persistent storage.
- Validate database-related stages in the staging checkout at a specific committed Git revision, independently of ongoing development. Do not modify source code in staging; correct defects in development and deploy the revised commit for validation.

Actual test execution is mandatory. Code inspection does not establish a test pass. Any required test that fails, is skipped, is blocked, or is otherwise not executed prevents stage completion.

## 5. Test Isolation and Safety

- Use the dedicated staging PostgreSQL instance and `arkkan_test` database defined in the Environment Architecture section of `TECHNICAL_REQ.md`, isolated from development and production at the PostgreSQL instance level, including cluster-wide roles.
- Use a shared mandatory safety guard before any automated database test, test setup, or cleanup. Verify the designated staging host, port, database and independently stored `arkkan_env.environment_identity` record; proceed only if the identity is exactly `staging`. Abort the database test, setup, or cleanup before proceeding if any verification fails, including missing, invalid or unreadable identity. No force option or bypass is permitted. Do not assume that a local database is disposable.
- Preserve the environment identity throughout test resets and cleanup. Keep staging infrastructure stable and automatically establish and reset application schema and test data to known states as required by each suite, including clean application initialization tests. Do not rely on manually maintained test data or previous test executions.
- Restrict infrastructure tests to the designated staging PostgreSQL instance. Before removing or recreating its container, verify the staging target using the mandatory safety guard. Container recreation tests must preserve the configured external persistent storage and verify the persistence and connectivity requirements defined in `TECHNICAL_REQ.md`, under Testing and Acceptance. Never delete persistent storage during tests or cleanup.
- Use temporary directories for filesystem tests.
- Keep test credentials outside source code and protect credentials and sensitive content in logs and reports.
- Ensure tests are reproducible and do not rely on undocumented environment state.

## 6. Test Evidence and Reporting

Retain one final test execution report per validated stage. Include:

- Execution date and actual commands executed.
- Test case identifiers and outcomes, distinguishing passed, failed, skipped, blocked, and not executed tests.
- Reasons for failed, skipped, blocked, or unexecuted tests, where applicable.
- Git commit identifier corresponding to the tested code.

Intermediate test runs do not require permanent records. Do not fabricate results or report unexecuted tests as passed.

After successful tests and both audits, create and verify the authorized Git checkpoint for the tested code, then finalize the report with that checkpoint identifier. Verify that the checkpoint contains the tested implementation, tests, and configuration. If any of these change after verification, rerun the applicable tests before reporting acceptance. The report references the tested checkpoint, not a later commit that records the report.

## 7. Failure Management

Investigate each test failure using execution evidence to distinguish software defects, test defects, and environmental issues. Correct confirmed defects within the authorized scope, rerun affected tests, and perform applicable regression testing.

After two consecutive unsuccessful attempts to fix the same defect, stop speculative modifications and follow the Deep Debug Process defined in the Software Developer prompt.

Report unresolved failures and their impact. Do not bypass, suppress, or weaken required tests to obtain a passing result.

## 8. Stage Acceptance

A stage is ready for user acceptance only when:

- All requirements and acceptance criteria applicable to the authorized stage are covered by automated tests; applicable tests from previous stages are included in regression testing.
- All required tests have been executed successfully.
- Both mandatory audit-and-correction passes have been completed: requirements and functional correctness; engineering quality and maintainability.
- Material defects have been corrected and affected tests and applicable regression tests rerun successfully.
- The test specification and final stage execution report are current.
- The required Git checkpoint has been created and verified in accordance with the implementation strategy.

The developer verifies compliance and reports actual evidence and outstanding limitations. The user retains final stage acceptance and explicit authorization to advance.

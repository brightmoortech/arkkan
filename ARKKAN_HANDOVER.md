# Arkkan development handover

**Date:** 2026-11-26

**Resume point:** Stage 5 WP1–WP5 complete; continue with WP6 when instructed.
Stage 4 acceptance is deferred until owner CLI testing.

**Audience:** A new development chat continuing the existing project.

This is a continuation snapshot, not a requirements source or authorization to
begin another stage. It supersedes the restart instructions in
`/Users/haitham/Downloads/ARKKAN_STAGE3_HANDOVER.md`, which described the older
WP1 checkpoint. Do not repeat completed Stage 3 packages.

## 1. Current state and completed plan

Stages 1 and 2 were accepted; Stage 2 acceptance was recorded on 2026-11-24.
All six Stage 3 work packages are implemented, reviewed and validated.
**The owner explicitly accepted Stage 3 on 2026-11-25:** “I approve stage 3.”
They chose to wait for the CLI before further manual testing and requested that
this decision be recorded, committed and pushed. No owner-run test results have
been supplied; acceptance does not add new test-execution evidence.

| Stage 3 package | Completed scope | Commit |
|---|---|---|
| WP1 | Shared response envelope and identifier/state/mode validation | `6463600` |
| WP2 | `add_resource_type`, `update_resource_type`, `delete_resource_type`, `add_resource`, `update_resource` | `3b61995` |
| WP3 | Content retrieval (three signatures), type listing, default lookup and resource metadata | `4ce0564` |
| WP4 | Single/bulk/global version deletion, explicit resource deletion and three lifecycle operations | `40aab53` |
| WP5 | Final runtime grants, initialization catalog checks and access reconciliation | `da6d921` |
| WP6 | Full regression, source inspections, two document audits and final execution report | `f092375` |

The result is 16 specified operations exposed through 18 public SQL signatures
and 37 ordered migrations. No Stage 3 implementation work is known to remain.
Python resource wrappers, CLI and end-to-end application workflows belong to
Stages 4, 5 and 6 respectively; they are not missing Stage 3 deliverables.

The owner subsequently authorized Stage 4, with **one work package at a time
to manage credits**. WP1 implements the private Python execution boundary in
`src/arkkan/_api.py`: parameterized SQL, per-call runtime configuration,
transaction/connection cleanup, decoded response validation and safe error
translation. WP2 adds four public read wrappers; WP3 adds five resource/type
administration wrappers; WP4 completes all 16 operations with lifecycle/deletion
wrappers. WP5 integration/regression and WP6 documentation closeout are complete.
Stage 4 is ready for owner acceptance. The owner subsequently deferred that
acceptance until CLI-based manual testing and explicitly authorized Stage 5.
No dependencies have been added.

### Stage 4 work packages and progress

This is the agreed execution plan for the Python API stage. Complete and commit
one package, then stop for the owner's next instruction. Package completion
does not constitute Stage 4 acceptance.

| Package | Planned deliverable | Current status | Evidence / remaining validation |
|---|---|---|---|
| WP1 — API foundation | Shared parameterized SQL execution, runtime configuration, transaction/connection handling, decoded JSON responses and safe errors | Complete for WP1 scope | Commit `adfa9d5`; 311 unit tests passed, including 39 new cases; two source audits completed. Database validation is recorded under WP5 below. |
| WP2 — Read operations | Content retrieval in all three call forms, type-based listing, default-version lookup and resource information; public exports and focused tests | Complete for WP2 scope | Commit `dcda13f`; 391 unit tests passed, including 80 new WP2 cases; two source audits completed. Database validation is recorded under WP5 below. |
| WP3 — Resource administration | Resource-type creation/update/deletion and resource creation/update; preserve omitted versus null values; focused tests | Complete for WP3 scope | 471 unit tests passed, including 80 new WP3 cases; two source audits completed. Commit `7319986`. Database validation is recorded under WP5 below. |
| WP4 — Lifecycle operations | Single/bulk/guarded state changes, version/resource deletion and cleanup; complete all 16 public operations with focused tests | Complete for WP4 scope | 592 unit tests passed, including 121 new WP4 cases; two source audits completed. Commit `d9c48dd`. Database validation is recorded under WP5 below. |
| WP5 — Integration and regression | PostgreSQL tests for every Python operation using reader/admin roles; permissions, response contracts, rollback and connection failures; cumulative prior-stage regression | Complete for WP5 scope | All 677 distinct cases passed across cumulative execution and targeted retest; see results and revision limits below. Test checkpoint `7e7d5be`. |
| WP6 — Documentation and handover | Final usage/development guidance, test traceability, Stage 4 execution report, registry and handover; final audits and acceptance checkpoint | Complete for WP6 scope | Final report created and registered; usage, development guidance, traceability and handover audited. Owner acceptance remains pending. |

**Progress:** 6 of 6 packages complete; owner acceptance pending. This is a package count,
not an estimate of effort completed. The owner requested a push before WP6;
all checkpoints through WP6 documentation commit `b5257ca` were pushed to
`origin/main`.

The durable [Stage 4 execution report](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE4.md)
consolidates execution, findings, traceability and limitations. WP6 changes no
application code, tests, SQL, dependencies or configuration. It adds no database
test run and makes no claim of owner acceptance.

WP5 validation evidence on 2026-11-25:

- Test checkpoint `79105de` introduced S4-030–035. Its first focused run produced
  six setup errors because `Path.open` does not accept `opener`; no API case passed.
- Correction checkpoint `b663ad8` uses builtin `open` with mode-0600 creation and
  verifies staging immediately before the real API connection, preventing the
  guard from translating the connection failure under test.
- Focused staging command: `.venv/bin/python -m pytest tests/integration/test_python_api.py -q --junitxml=/private/tmp/arkkan-wp5-b663ad8-focused.xml`.
  Result: **6 passed in 354.24 seconds**, no failures/errors/skips.
- Cumulative staging command at `b663ad8`: `.venv/bin/python -m pytest tests/unit tests/integration -q --junitxml=/private/tmp/arkkan-stage4-b663ad8.xml`.
  Result: **670 passed, 1 failed, 6 setup errors in 1587.20 seconds**, no skips.
  S2-030 removed the staging container, but immediate setup reported port 5442
  unavailable. The six Python API cases then correctly failed their safety guards.
  A later guarded setup succeeded. The surviving persistence marker and non-login
  role were verified and removed with restrictive cleanup; storage and identity
  were preserved. No unrelated container or port configuration was changed.
- Audit correction `7e7d5be` makes rollback-test helper creation and cleanup atomic.
  Development unit rerun: **592 passed in 1.11 seconds**.
- Supplemental staging command at `7e7d5be`: `.venv/bin/python -m pytest tests/unit tests/integration/test_environment_management.py tests/integration/test_python_api.py -q --junitxml=/private/tmp/arkkan-wp5-7e7d5be-retest.xml`.
  Result: **605 passed in 465.16 seconds**, no failures/errors/skips: 592 unit,
  7 environment-management and 6 Python API tests. S2-030 and every previously
  blocked API case passed; the rollback-test correction passed at this revision.
- Combined JUnit case matching confirms **677 distinct cases have passed**:
  592 unit and 85 integration, covering S1-001–006, S2-001–068, S3-001–032 and
  S4-001–035. This is evidence across two runs, not a single clean full-suite run
  at `7e7d5be`. Unaffected tests retain their successful evidence from `b663ad8`.
- Post-retest `.venv/bin/python scripts/manage_environment.py check` passed in
  staging. The staging checkout is clean; application fixtures were cleaned up.
- Tests use real admin/reader authentication with temporary credentials, validate
  all 16 operations, enforce reader denial, check invalid-input preservation,
  injected rollback and connection failure/recovery, and assert connection closure.
- No application, SQL, dependency or configuration changes were required. The
  port conflict was transient in observation; its underlying cause is not established.
  The conflict did not recur during the environment-management retest. If it
  recurs, investigate the port owner/release timing before changing provisioning.
- Supplementary JUnit SHA-256 checksums (temporary files may be cleaned up):
  focused `b663ad8`: `cf2bfd2bb018146f2f66dbfdfc5813530fbd232047e672ada1ad606cd0f18231`;
  cumulative `b663ad8`: `908458f92831bc87c6d0e2d45750428824f7a69d205e386f1b4f7e1ac062ba01`;
  retest `7e7d5be`: `b72d16dd97595865f39e114a206b057719e84868dbc172df756bf077e037b4c6`.

WP5 source audits checked real authentication, all operation contracts, failure
translation, rollback, fixture isolation and cleanup, then maintainability and
reuse of existing guarded helpers. Corrections addressed protected password-file
creation, exception isolation and atomic helper setup/cleanup. All affected cases
passed afterward; no unresolved application defect was found. README, DEVELOPMENT,
TEST_SPECIFICATION and this handover completed content/compliance and quality
audits before the documentation checkpoint. The final Stage 4 report now consolidates this evidence.

WP4 verification on 2026-11-25: `.venv/bin/python -m pytest tests/unit -q`
passed **592 tests**, including 121 new cases covering S4-024–029. All 16 public
operations are exported. Lifecycle/deletion wrappers reuse the execution boundary
and retain SQL ownership of transitions, default policy and deletion eligibility.
No database tests were run for WP4.

WP4 source audits checked contracts, defaults, boolean/null handling, response
preservation, SQL policy ownership and regressions, then maintainability and test
coverage. Review added boolean rejection coverage in text positions and restored
alphabetical public exports. Both passes completed with no unresolved finding.

WP3 verification on 2026-11-25: `.venv/bin/python -m pytest tests/unit -q`
passed **471 tests**, including 80 new cases covering S4-017–023. Nine public
operations were exported at that checkpoint. `src/arkkan/_write.py` binds text
arguments and uses Psycopg JSONB adaptation for metadata changes, preserving omitted keys, nulls,
empty strings and the caller's dictionary. SQL retains key, target, permission,
immutability and state validation. No database tests were run for WP3.

WP3 source reviews checked contract/default coverage, argument types, JSONB
serialization, safe errors, policy ownership, public exports and regression risk.
Review isolated mutable test inputs so parameterized cases cannot affect one
another; direct JSONB objects are rejected in text argument positions. Both
source audits are complete with no unresolved WP3 finding.

WP2 verification on 2026-11-25: `.venv/bin/python -m pytest tests/unit -q`
passed **391 tests**, including 80 new cases covering S4-010–016. The wrappers in
`src/arkkan/_read.py` are exported from `arkkan`; they use the WP1 boundary and
preserve omitted versus explicit-null arguments. Mode without version and
unsupported Python types return safe errors before connecting. Malformed Python
call signatures raise `TypeError`. PostgreSQL retains value validation and
selection policy. No database tests were run for WP2.

WP2 source reviews checked (1) all read contracts, argument routing, null handling,
response preservation and scope, and (2) typing, public exports, dependency
reuse and regression risk. Review clarified the documented `TypeError` behavior
and added keyword-call coverage. No unresolved WP2 source finding remains.

WP1 verification on 2026-11-25: `.venv/bin/python -m pytest tests/unit -q`
passed **311 tests**, including 39 new cases covering S4-001–009. No database
tests were run for WP1; its database validation is recorded under WP5 above.
The package's source and documentation are committed together; locate its
checkpoint with `git log -1 -- src/arkkan/_api.py`. No Stage 4 acceptance is claimed.

WP1 review findings: correctness review removed a redundant rollback attempt
after rollback failure and added coverage for that path, including combined
commit/rollback failure. Quality review clarified test typing and formatting.
Both passes checked cleanup, parameter binding, safe diagnostics and the absence
of duplicated lifecycle rules. No unresolved WP1 source finding remains.

### Stage 5 work packages and progress

The owner authorized Stage 5 after explicitly deferring Stage 4 acceptance until
CLI-based manual testing. Continue one package per turn, test and commit it,
then stop. This sequencing decision does not imply acceptance of either stage.

| Package | Deliverable | Status |
|---|---|---|
| WP1 | Installable executable, parser/help, shared output/error handling, four read commands and local tests | Complete |
| WP2 | Resource/type creation and metadata updates, UTF-8 files/stdin, metadata clearing and local tests | Complete |
| WP3 | Lifecycle/deletion commands and local tests; complete all 16 command mappings | Complete |
| WP4 | Real CLI PostgreSQL tests, role authorization, password-file authentication and representative command workflows | Complete |
| WP5 | Cumulative prior-stage and CLI regression, corrections and verification | Complete |
| WP6 | Complete usage guidance, final Stage 5 report, audits and handover | Pending |

WP1 implementation checkpoint `0489e93` and documentation `ea94b08` are pushed.
WP1 adds `src/arkkan/_cli.py` and the console entry point in `pyproject.toml`.
It uses standard-library argparse and the public Python API; no SQL or dependency
changes. Installation refresh succeeded. The final local unit run passed
**658 tests in 1.27 seconds**, including **66 CLI cases**, with no failures,
errors or skips. No database tests ran for WP1. Both source and documentation
review passes completed; WP4 supplies the later real CLI database validation.
See the [Stage 5 report](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE5.md) and
[CLI usage](README.md#cli-reference). The report is progressive until closeout.

WP2 implementation checkpoint `6b591c7` and documentation `37f2bca` are pushed. WP2 adds
`resource add`, `resource update`, `type add` and `type update`, bringing the CLI
to eight of 16 operation mappings. Strict UTF-8 file/stdin reads preserve newlines;
invalid input fails before an API call. Metadata updates distinguish omitted,
empty and cleared fields. PostgreSQL retains business policy and authorization.
No dependencies, SQL or Python API contracts changed. Final development unit
run: **803 passed in 1.51 seconds**, including 145 new WP2 cases. Both source
and document audit passes completed. No database tests ran; real CLI validation
remains WP4. One package at a time remains the agreed execution boundary.

WP3 implementation checkpoint `dd0bff2` and documentation `6b8ef63` are pushed.
WP3 adds all eight lifecycle/deletion commands, including `type delete`, completing all 16 CLI
operation mappings. The final development unit run passed **931 tests in 1.77
seconds**, including 128 new WP3 cases. Two source audits checked command/API
contracts, force scope, output counts, API boundaries and maintainability.
No database tests ran and no SQL, dependencies or public API contracts changed.
WP4 now supplies real executable workflows in guarded staging, separately from
local doubles and earlier Python API integration evidence.

WP4 adds five cases in `tests/e2e/test_cli_workflows.py`, covering all 16 commands,
both roles, exact UTF-8 file/stdin retrieval, metadata empty/null persistence,
lifecycle/deletion policies, all 12 reader write denials, missing-password failure,
local-input rejection and database rollback. Tests launch the installed executable
outside the checkout with explicit target settings and temporary mode-0600
password files; the safety guard precedes each invocation and database operation.
Temporary credentials are removed; operator credentials and development are untouched.
Initial checkpoint `c1db1fc` passed all five e2e cases in 337.77 seconds. Audit
corrections `93a5286` and `a226b9e` strengthen persisted metadata clearing and
prevent assertion diagnostics from displaying password-file contents. Final
unit/e2e verification at `a226b9e` passed **936 tests in 345.40 seconds**, with
no failures, errors or skips. The post-run staging environment check passed.
Both source and document audit passes are complete; see the Stage 5 report.
WP4 commits remain local, not pushed. Stage 5 acceptance and Stage 4 owner
acceptance remain pending.

WP5 cumulative regression passed **1,021 tests in 2,288.11 seconds** at
`44a10aaebe99cf780f01fe3e5f10752e023bfd14` on 2026-11-26: 931 unit,
85 integration and five e2e cases, with no failures, errors or skips. All 170
specified identifiers were present. This is one clean cumulative run at that
revision, including container recreation, all prior-stage tests and CLI workflows.
The earlier port conflict did not recur; its original cause remains unestablished.
Both pre-run and post-run staging checks passed; the staging checkout is clean.
No code, tests, SQL, dependencies or configuration needed correction. Two source
review passes and two document audit passes completed; see the Stage 5 report
for scope, command, checksum and limitations. WP5 delivery remains local.

Next is WP6: finalize Stage 5 usage guidance, execution report, audits and
handover for owner review. Do not start Stage 6 or claim owner acceptance.

## 2. Repository checkpoints and delivery

- Development: `/Users/haitham/development/develop/arkkan`, branch `main`.
- Remote `origin/main` was pushed through Stage 5 WP3 documentation, `6b8ef63`.
- Pushed Stage 4 WP5 test commits are: `79105de`, `b663ad8`, and
  `7e7d5befb5abcdb7f5175acb93ca5c820f457f1e`. The last changes only the rollback
  integration test's helper transactions. Application source, SQL and configuration
  are identical across these checkpoints.
- Staging: `/Users/haitham/development/stage/arkkan`, detached at `44a10aa` for
  Stage 5 WP5 cumulative regression. Earlier Stage 4 runs and their revisions remain
  recorded above; they are not evidence of current cumulative regression.
- Stage 3 historical tested implementation:
  `da6d921758f07356a5fefa340ad63678a09b88d6`; documentation closeout:
  `f092375f095c59d1b7ad942c323b98e401221ad3`. Both were pushed. Later commits
  recorded owner acceptance and the Stage 4 packages above.
- An unrelated local table-formatting edit in `arkkan.wiki/TECHNICAL_REQ.md`
  remains excluded from WP5 and WP6. Preserve it on resumption.

The owner prefers repository commits as delivery. Do not produce replacement
ZIPs unless requested. The earlier ZIP-based handover workflow is obsolete.

## 3. Stage 3 validation and audit evidence

The coding assistant executed tests on the owner's Mac, using the project's
local virtual environments and isolated staging PostgreSQL instance.

| Execution | Actual outcome |
|---|---|
| Development unit suite | 272 passed |
| Staging unit and integration suite at `da6d921` | 351 passed: 272 unit + 79 integration; zero failures, errors or skips |
| Full suite duration | 1585.98 seconds, approximately 26 minutes |
| Post-suite staging environment check | Passed |

All 106 test identifiers were represented: S1-001–006, S2-001–068 and S3-001–032.
The suite covers the whole cumulative implementation, including clean initialization,
dry runs, reruns, upgrade preservation, rollback, protected types, reads/writes,
lifecycle and deletion policy, concurrency, role permissions and container persistence.

Durable evidence is in
[TEST_EXECUTION_PHASE1_STAGE3.md](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE3.md).
The supplementary JUnit file was written to
`/private/tmp/arkkan-stage3-da6d921.xml`; it may not survive temporary-file cleanup.
Its checksum is retained in the report. Test definitions and traceability are
in [TEST_SPECIFICATION.md](arkkan.wiki/TEST_SPECIFICATION.md).

Completed source reviews covered (1) requirements and correctness, (2) engineering
quality, maintainability and regression risk, plus a distinct reviewer-perspective
inspection of security, concurrency, transaction boundaries and test effectiveness.
These were separate passes by the coding assistant, not external independent reviewers.
README, DEVELOPMENT, TEST_SPECIFICATION, AGENTS and the Stage 3 execution report
each received content/compliance and document-quality audits before WP6 was committed.

## 4. Open items, known issues and deferred work

1. **Stage 3 is accepted.** The owner will wait for the CLI before further manual
   testing. No additional owner validation is a pending Stage 3 acceptance gate.
2. **Stage 4 WP1–WP6 are complete; owner acceptance is pending.**
   Final documentation and the Stage 4 execution report are in the repository.
   The transient S2-030 port conflict and successful retest are recorded above;
   its root cause was not established.
   The owner explicitly authorized Stage 5 while deferring Stage 4 acceptance
   until the CLI supports manual validation.
3. **No unresolved Stage 3 defect is recorded.** S3-KI-001 through S3-KI-010 are
   retained as resolved findings in the final execution report. Do not delete that
   history or treat resolved findings as unfinished work. Notable corrections were
   freezing bulk-selection IDs before default demotion, disambiguating the add-resource
   conflict constraint, strengthening preservation/concurrency assertions, and
   revoking test-role CONNECT grants before restrictive role cleanup.
4. **Development database application state is not established by this handover.**
   The final automated suite did not initialize development. Check its current state
   read-only before proposing a manual apply; never use it for automated DB tests.
5. **Staging tests clean up application objects.** A successful suite does not leave
   a ready-to-use application dataset. Do not apply/reset anything while an owner
   validation run may be active.
6. **Deferred improvements remain deferred.** See [BACKLOG.md](arkkan.wiki/BACKLOG.md):
   UX-01–05, ENV-01–02 and REC-01. Backup/recovery utilities remain Phase 4 and belong
   in Arkkan, not pyprojectgen. Workflow terminology consolidation is deferred.
7. **Recovery evidence remains limited.** Stage 2 recorded a same-cluster logical
   backup/restore drill. The exact manual procedure in DEVELOPMENT retains its
   pending-validation label; Stage 3 did not rerun it or establish full-cluster recovery.

## 5. Read first and preserve these decisions

Start with the original prompt, then [AGENTS.md](AGENTS.md) and its task-specific
reading sequence. The following externally supplied files are local to this host:

- `/Users/haitham/development/ai/ai-prompt-library/prompts/llm.software.developer.prompt.md`
- `/Users/haitham/development/ai/ai-prompt-library/extensions/software.architecture.principles.md`
- `/Users/haitham/development/ai/ai-prompt-library/extensions/llm.document.governance.process.md`
- `/Users/haitham/development/ai/ai-prompt-library/extensions/llm.general.clarification.process.md`

For implementation, read complete FUNCTIONAL_REQ, TECHNICAL_REQ, CODING_CONVENTIONS,
TESTING, DEVELOPMENT and TEST_SPECIFICATION in `arkkan.wiki`, plus applicable reports.
Read DOCUMENT_GOVERNANCE before documentation changes. Requirements remain authoritative;
distinguish attached-document guidance from the user's current request.

- PostgreSQL owns business rules. Python wrappers must use parameterized SQL,
  preserve the common JSON response, translate database errors at the API boundary,
  and manage connections/transactions without duplicating lifecycle rules.
- Public SQL lives in `arkkan_api`; internal helpers and tables live in `arkkan`.
  Runtime roles have function permissions, not direct table/helper access.
- Every completed SQL API response goes through `arkkan.api_response`; retain safe
  error messages, qualified references and safe function search paths.
- Resource mutations serialize on the parent definition. Bulk selection is captured
  before default demotion; the unique default index remains a backstop.
- Keep `_migration_workflow.py` and `_initialization_connection.py` generic, separate
  from `_db_migrations.py` and `sql/migrations/`. Initialization defaults to read-only
  planning; only `--apply` writes. Preserve compliant objects, data and credentials;
  reject conflicting definitions rather than replacing them.
- Implement/fix in development, commit, then deploy an exact revision to staging.
  Never edit staging source or bypass `_staging_connection` safety checks.
- Keep both source audit passes and a prioritized findings register. After two
  unsuccessful fixes of one defect, use the original prompt's Deep Debug Process.
- Keep one test specification and one final execution report per stage. Audit actual
  final documents twice and preserve unrelated content. Do not fill intentionally
  blank README sections prematurely.
- Stage 3 was authorized autonomously without intermediate package approvals.
  That does not authorize later stages. Commit completed authorized packages;
  verify the current request before publishing new work.

## 6. Environment and owner validation

| Setting | Development | Staging |
|---|---|---|
| Container | `arkkan-db-dev` | `arkkan-db-test` |
| Database | `arkkan_dev` | `arkkan_test` |
| Host port | 5441 | 5442 |
| Independent identity | `development` | `staging` |

Baseline: macOS, Python 3.12.10, pytest 9.1.1, Psycopg binary 3.3.9 and PostgreSQL
`18.7-bookworm`. Each checkout has its own `.venv` and ignored `.env`. Storage is
external under `~/development/data/arkkan/`. Credentials are operator-managed;
reuse protected files without displaying, committing or recreating them.

The owner was given this Stage 3 validation sequence and subsequently chose
to wait for the CLI. It targets the historical Stage 3 checkpoint. It remains an
optional reference, not a pending acceptance requirement or evidence of owner
execution. Preserve local changes before switching revisions.
Do not start a second suite against the same staging database concurrently.

```bash
cd /Users/haitham/development/stage/arkkan
git status --short
git fetch origin
git switch --detach f092375
.venv/bin/python scripts/manage_environment.py setup
.venv/bin/python scripts/manage_environment.py check
.venv/bin/python -m pytest tests/unit tests/integration -v \
  --junitxml=/private/tmp/arkkan-stage3-owner-validation.xml
.venv/bin/python scripts/manage_environment.py check
```

Expected baseline: 351 passed, no failures/skips, then a successful environment
check. `setup` can start a stopped verified container and reuse existing storage.
Automated tests reset application objects and test data; never run them against
development or production. Investigate failures and fix in development before
redeploying and rerunning affected tests and applicable regressions.

## 7. Pickup instruction for the new chat

Read this handover and governing sources; inspect Git status, recent commits and
the staging checkout without disturbing an active validation run. Preserve newer
owner changes. Review any supplied validation results and resolve confirmed issues
within the authorized scope. Stage 3 acceptance is already recorded; do not ask
the owner to accept it again. Stage 4 is ready for owner acceptance. Review
[its final report](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE4.md), including the
transient port conflict and successful rerun; do not describe it as one clean
full-suite run at the final test revision.

Continue Stage 5 with WP6 when the owner requests the next package. Stage 5 is
authorized; do not ask for Stage 4 acceptance before completing CLI closeout. Retain
one work package at a time unless the owner changes that preference. Use the
public Python API; do not introduce new database operations or duplicate SQL
business rules. Stage 6 remains unauthorized.

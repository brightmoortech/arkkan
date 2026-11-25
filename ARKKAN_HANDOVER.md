# Arkkan development handover

**Date:** 2026-11-25

**Resume point:** Stage 4 WP2 implemented and unit-tested; stop before WP3

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
Python resource wrappers, CLI and end-to-end application workflows remain
Stages 4, 5 and 6 respectively; they are not missing Stage 3 deliverables.

The owner subsequently authorized Stage 4, with **one work package at a time
to manage credits**. WP1 implements the private Python execution boundary in
`src/arkkan/_api.py`: parameterized SQL, per-call runtime configuration,
transaction/connection cleanup, decoded response validation and safe error
translation. WP2 adds the four public read wrappers. WP3 requires the owner's
next instruction; Stage 5 is not authorized. No dependencies have been added.

### Stage 4 work packages and progress

This is the agreed execution plan for the Python API stage. Complete and commit
one package, then stop for the owner's next instruction. Package completion
does not constitute Stage 4 acceptance.

| Package | Planned deliverable | Current status | Evidence / remaining validation |
|---|---|---|---|
| WP1 — API foundation | Shared parameterized SQL execution, runtime configuration, transaction/connection handling, decoded JSON responses and safe errors | Complete for WP1 scope | Commit `adfa9d5`; 311 unit tests passed, including 39 new cases; two source audits completed. Real database validation remains pending in WP5. |
| WP2 — Read operations | Content retrieval in all three call forms, type-based listing, default-version lookup and resource information; public exports and focused tests | Complete for WP2 scope | 391 unit tests passed, including 80 new WP2 cases; two source audits completed. Locate the package commit with `git log -1 -- src/arkkan/_read.py`. Real database validation remains pending in WP5. |
| WP3 — Resource administration | Resource-type creation/update/deletion and resource creation/update; preserve omitted versus null values; focused tests | Not started — next package | Await owner's instruction. |
| WP4 — Lifecycle operations | Single/bulk/guarded state changes, version/resource deletion and cleanup; complete all 16 public operations with focused tests | Not started | Follows WP3. |
| WP5 — Integration and regression | PostgreSQL tests for every Python operation using reader/admin roles; permissions, response contracts, rollback and connection failures; cumulative prior-stage regression | Not started | Run against a committed revision in guarded staging; record actual results and resolve failures. |
| WP6 — Documentation and handover | Final usage/development guidance, test traceability, Stage 4 execution report, registry and handover; final audits and acceptance checkpoint | Not started | Package-level documentation is maintained incrementally. `TEST_EXECUTION_PHASE1_STAGE4.md` has not yet been created; Stage 4 acceptance remains pending. |

**Progress:** 2 of 6 packages complete; WP3–WP6 not started. This is a package
count, not an estimate of effort completed. Stage 4 delivery is through local
commits; these have not been pushed. No Stage 4 PostgreSQL integration results
are available yet.

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
tests were run for WP1; actual PostgreSQL integration and the cumulative full
regression remain pending for Stage 4. The package's source and documentation
are committed together; locate its checkpoint with
`git log -1 -- src/arkkan/_api.py`. No Stage 4 acceptance is claimed.

WP1 review findings: correctness review removed a redundant rollback attempt
after rollback failure and added coverage for that path, including combined
commit/rollback failure. Quality review clarified test typing and formatting.
Both passes checked cleanup, parameter binding, safe diagnostics and the absence
of duplicated lifecycle rules. No unresolved WP1 source finding remains.

## 2. Repository checkpoints and delivery

- Development: `/Users/haitham/development/develop/arkkan`, branch `main`.
- Pushed closeout: `f092375f095c59d1b7ad942c323b98e401221ad3`.
- Tested implementation: `da6d921758f07356a5fefa340ad63678a09b88d6`.
- The closeout commit changes documentation only; source, tests and configuration
  match the tested implementation.
- All Stage 3 package commits were pushed to `origin/main`; the push completed successfully.
  Before this acceptance update, local `HEAD` and `origin/main` both resolved to
  `f092375`. The handover and acceptance update are delivered in a later documentation commit.
- Staging: `/Users/haitham/development/stage/arkkan`, clean detached checkout at
  `f092375` when inspected for this handover. The assistant's recorded suite ran
  earlier at `da6d921`. The newer staging checkout is not evidence of a new test run.
- This handover and its AGENTS registry entry were created after `f092375`.
  The acceptance update also synchronizes README and the Stage 3 execution report.
  An unrelated local table-formatting edit in `arkkan.wiki/TECHNICAL_REQ.md` was
  present during this update and excluded from its commit. Preserve it on resumption.

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
2. **Stage 4 WP1 and WP2 are implemented; WP3 awaits the owner's instruction.**
   Remaining packages cover administration wrappers, lifecycle
   wrappers, integration/regression, and final documentation/acceptance.
   Stage 4 authorization does not authorize Stage 5.
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

- PostgreSQL owns business rules. Future Python wrappers must use parameterized SQL,
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

The owner was given this validation sequence and subsequently chose to wait for
the CLI. It remains an optional reference, not a pending acceptance requirement
or evidence of owner execution. Preserve local changes before switching revisions.
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
the owner to accept it again. Stop after Stage 4 WP2 until instructed to start WP3.

On the next instruction, implement WP3 administration wrappers and tests using the
WP1 execution boundary. Continue one package at a time, committing each completed
package and stopping for the owner's next instruction.
Use the existing SQL API and configuration infrastructure; do not invent extra public
operations or begin CLI work. Stage 4 must pass unit and staging integration tests
for all specified operations and errors before its own acceptance checkpoint.

# arkkan Test Execution Report

## Phase 1, Stage 3: PostgreSQL API

- Execution date: 2026-11-25.
- Implementation checkpoint: `da6d921758f07356a5fefa340ad63678a09b88d6` (WP5), deployed as a detached staging checkout.
- Status: all automated validation passed; explicitly accepted by the owner on 2026-11-25.
- Environment: the owner's macOS host, Python 3.12.10, pytest 9.1.1,
  Psycopg binary 3.3.9, PostgreSQL `18.7-bookworm` in `arkkan-db-test`;
  database `arkkan_test`, host port 5442.
- Evidence: commands executed by the coding assistant on the owner's host,
  not owner-reported results or a separate assistant database environment.
- Authority: [Functional Requirements](FUNCTIONAL_REQ.md),
  [Technical Requirements](TECHNICAL_REQ.md), [Testing Governance](TESTING.md),
  and [Test Specification](TEST_SPECIFICATION.md). Stage boundaries follow
  Technical Requirements, Development & Deployment / Phase 1 Implementation Strategy.

## 1. Delivered scope

| Work package | Deliverable | Commit |
|---|---|---|
| WP1 | Shared response and validation helpers | `6463600` |
| WP2 | Resource and type creation/update operations | `3b61995` |
| WP3 | Read operations and retrieval selection | `4ce0564` |
| WP4 | Deletion, lifecycle transitions and bulk policies | `40aab53` |
| WP5 | Runtime grants and complete initialization | `da6d921` |
| WP6 | Consolidated regression, inspections and this closeout report | Report commit follows tested checkpoint |

The complete implementation has 37 ordered migrations and 18 public SQL
signatures for 16 operations, including the three `get_resource_content` call
forms. PostgreSQL owns resource policy; Python resource wrappers and CLI work
belong to later stages. All runtime access goes through the authorized
`arkkan_api` functions. Internal helpers and application tables remain private.

## 2. Execution evidence

Development unit command: `.venv/bin/python -m pytest tests/unit -q`.
Result: 272 passed. This does not establish database behavior.

Staging was clean before deployment. The exact local development commit was
fetched into `/Users/haitham/development/stage/arkkan` and checked out detached.
The stopped staging container was started using the existing configuration:

```bash
.venv/bin/python scripts/manage_environment.py setup
```

Setup succeeded while preserving existing storage and the independent staging
identity. Full staging command:

```bash
.venv/bin/python -m pytest tests/unit tests/integration -q --maxfail=1 --junitxml=/private/tmp/arkkan-stage3-da6d921.xml
```

Result: **351 passed in 1585.98 seconds (26 minutes 25 seconds)**; zero failures,
errors or skips. The JUnit record contains all 106 specified test identifiers,
expanded into 272 unit and 79 integration cases. No required automated case
was blocked or left unexecuted.

| Test identifiers | Unit cases | Integration cases | Outcome |
|---|---:|---:|---|
| S1-001–S1-006 | 11 | 0 | All passed |
| S2-001–S2-068 | 177 | 21 | All passed |
| S3-001–S3-032 | 84 | 58 | All passed |
| Total | 272 | 79 | 351 passed |

The test specification maps each identifier to its requirement and executable
function. Parameterized cases and internal matrices cover additional inputs;
only pytest's expanded cases are counted here. Results were checked against
`/private/tmp/arkkan-stage3-da6d921.xml`, whose SHA-256 is
`2b672c2e37bbf69d71a4dd86d8e4e2dc91b2cc2d89b699d5e23fe3d8fa93edcb`.
That local temporary artifact is supplementary; this report retains the durable
outcomes and traceability. Staging remained clean at the exact tested revision.
The post-suite `.venv/bin/python scripts/manage_environment.py check` also
succeeded. Application fixtures clean up their objects; this test pass does
not mean staging retains an initialized application dataset.

| Stage 3 validation gate | Passing evidence |
|---|---|
| Common envelope, validation and private helpers | S3-001–006 |
| Resource/type writes, preservation and error atomicity | S3-009–016 |
| Reads, availability, fallback and metadata | S3-022–023 |
| Lifecycle policies, bulk membership and deletion | S3-024–027 |
| Serialized writes and competing defaults | S3-020–021, S3-032 |
| Runtime role permissions and rejected excessive grants | S2-064, S3-004/017/028/030 |
| Full clean initialization, read-only checks and reruns | S2-060–061, S3-007/019/029 |
| Conflict rejection and step rollback | S2-052–055/065–067, S3-005/018/029–031 |
| Prior-stage isolation, identity and persistence | All S1/S2 cases, including S2-027–030 |

All database test setup, connections and cleanup use the mandatory staging
guard. Application resets use restrictive drops of known objects and revoke
only test-role CONNECT grants on the designated database before role cleanup.
Environment identity and external PostgreSQL storage are preserved. No
automated database tests ran against development.

## 3. Review and correction evidence

Requirements/correctness review compared the 16 operation contracts and
initialization requirements with migration SQL, catalog verification, and
test assertions. It covered literal identifiers, immutable fields, null versus
omitted updates, retrieval availability/fallback, all lifecycle transitions,
default preservation, obsolete-only deletion, response payloads, atomicity,
and role capabilities.

The separate engineering-quality pass inspected safe search paths, qualified
references, specific exception handling, private helper reuse, migration
transaction boundaries, parent-row locking and deterministic cleanup lock
order. The generic migration workflow remains independent of Arkkan policy.
No dependencies were introduced or upgraded.

A further reviewer-perspective inspection challenged the implementation using
unauthorized execution paths, competing default changes, selection membership
after default demotion, injected failures after mutation, and test assertions
that could pass without observing a lock. This was a distinct review by the
same coding assistant, not an independent external reviewer. No additional
material source defect was identified during the final consolidation.

Documentation audits cover README, DEVELOPMENT, TEST_SPECIFICATION, AGENTS
and this report. Content review compares status, counts, commands, requirements
traceability and checkpoint claims against the source and actual JUnit evidence.
Quality review checks reader clarity, terminology, links and separation of
implementation, validation and user acceptance. S3-KI-010 records the stale
status and upgrade-description corrections. Historical reports and unrelated
guidance remain unchanged.

## 4. Known Issues

This register retains corrected findings. WP1 priorities were not recorded in
the handover and are not reconstructed. Later priorities reflect the recorded
implementation reviews or the closeout assessment.

| ID | Severity / priority | Component and finding | Correction and verification |
|---|---|---|---|
| S3-KI-001 | Major / not recorded | Response helper permitted invalid JSON payload types. | WP1 restricted payload types; S3-001/002/006 cover the response contract and invalid arguments. Resolved; corresponding staging cases passed. |
| S3-KI-002 | Major / not recorded | Test cleanup omitted new private functions, preventing repeatable resets. | Restrictive cleanup includes private helpers; initialization and repeated guarded fixtures exercise cleanup. Resolved; corresponding staging cases passed. |
| S3-KI-003 | Minor / not recorded | Initialization regression did not compare function object identifiers. | Catalog snapshots now include function OIDs; S2-060, S3-007/019 verify preservation. Resolved; corresponding staging cases passed. |
| S3-KI-004 | Major / High | `add_resource` used an ambiguous conflict target sharing a PL/pgSQL argument name. | Named unique constraint replaces the ambiguous target; S3-012/020 cover creation and competing creators. Resolved; corresponding staging cases passed. |
| S3-KI-005 | Minor / Medium | Update/concurrency tests lacked some preservation and outcome assertions. | Strengthened omitted-field, competing-type and lock-observation assertions in S3-015/020/021. Resolved; corresponding staging cases passed. |
| S3-KI-006 | Minor / Low | Development documentation retained an obsolete migration count. | Updated cumulative inventory to 37; manifest and initialization tests passed and verify that inventory; resolved. |
| S3-KI-007 | Major / High | Bulk default promotion could include the demoted old default in an enabled-state selection. | Freeze selected version IDs before demotion; S3-025 checks membership and exactly one default. Resolved; corresponding staging cases passed. |
| S3-KI-008 | Major / Medium | Explicit database CONNECT grants could prevent test-role cleanup. | Revoke only CONNECT on the guarded test database before restrictive role removal; full repeated initialization fixtures exercise the fix. Resolved; corresponding staging cases passed. |
| S3-KI-009 | Minor / Low | Initialization entry-point status still described the API as unavailable. | Updated the status to describe complete Stage 3 function/grant verification; source inspected and entry-point tests passed; resolved. |
| S3-KI-010 | Minor / Low | Test specification retained pending-development language and described the WP1 upgrade as only five steps. | Reconciled checkpoint counts, complete-upgrade wording, payload descriptions and implementation status against final source; corrected wording verified against source and execution evidence; resolved. |

## 5. Acceptance and limitations

Stage 3 automated validation passed. All recorded findings are resolved; no
unresolved Critical or Major issue was identified. The owner explicitly accepted
Stage 3 on 2026-11-25 and chose to wait for the CLI before further manual testing.
No additional owner-run test results were supplied. Stage 4 requires separate
explicit authorization.
No Python API, CLI, Linux application deployment, production-readiness claim,
or new backup/recovery drill is included. The accepted Stage 2 evidence and
its manual-recovery limitations remain in its historical execution report.

The later documentation commit must leave the tested implementation, tests and
configuration unchanged. Any subsequent changes to those files require
applicable testing before acceptance.

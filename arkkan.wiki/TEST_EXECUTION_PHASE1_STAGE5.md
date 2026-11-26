# arkkan Test Execution Report

## Phase 1, Stage 5: CLI

**Status:** In progress; WP1–WP4 complete; WP5–WP6 pending. This report accumulates
actual evidence and will be finalized at Stage 5 closeout. Stage 4 acceptance
is deferred until the owner can test through the CLI. The owner explicitly
authorized Stage 5; no owner acceptance or manual test results are claimed.

## 1. Work packages

| Package | Scope | Status |
|---|---|---|
| WP1 | Installable executable, help, output/errors and four read commands | Complete; checkpoint `0489e93` |
| WP2 | Resource/type creation and metadata updates, UTF-8 file/stdin input and clearing | Complete; checkpoint `6b591c7` |
| WP3 | Lifecycle/deletion commands; all 16 command mappings | Complete; checkpoint `dd0bff2` |
| WP4 | Real PostgreSQL CLI workflows, role authorization and password-file authentication | Complete; checkpoint `a226b9e` |
| WP5 | Cumulative regression, corrections and verification | Pending |
| WP6 | Final usage documentation, report, audits and handover | Pending |

## 2. WP1 execution evidence

- Date: 2026-11-26, on the owner's Mac in the development checkout.
- Tested source checkpoint: `0489e9331661f7622b15569a81537f040f9740e0`.
  Tests ran before committing; the checkpoint contains the tested implementation,
  tests and entry-point metadata. The later documentation commit changes none of them.
- Runtime: existing project virtual environment with Python 3.12.10 and pytest 9.1.1.
- Installation refresh succeeded using existing dependencies:

```bash
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
```

The installed executable was tested from a temporary directory with libpq
variables removed. Help succeeded without requiring database configuration.
This verifies installation into the existing environment, not a fresh-environment
or Linux installation.

Final regression command:

```bash
.venv/bin/python -m pytest tests/unit -q --junitxml=/private/tmp/arkkan-stage5-wp1.xml
```

**Result: 658 passed in 1.27 seconds; zero failures, errors or skips.** This
includes 592 prior-stage unit cases and 66 CLI cases under S5-001–008. An earlier
run passed 653 cases before JSON-content coverage was expanded during review.

| IDs | Verified scope | Outcome |
|---|---|---|
| S5-001–002 | Syntax rejection, option scope, help at each implemented level, no database calls | Passed |
| S5-003–004 | Four read mappings, defaults/modes, literal arguments, exact content and JSON output | Passed |
| S5-005–006 | Human metadata, empty results, API errors, stdout/stderr and exit codes | Passed |
| S5-007–008 | Missing configuration and installed executable help outside the checkout | Passed |

JUnit artifact: `/private/tmp/arkkan-stage5-wp1.xml`; temporary files may be
removed by host cleanup. SHA-256: `eb855f3b9ebf41ec445352706fb696dd188d689fafb8137dfe5030e734390efc`.
Definitions and requirement mappings are in [TEST_SPECIFICATION.md](TEST_SPECIFICATION.md).

## 3. WP1 audits and corrections

Two source passes checked WP1 against the CLI contracts in TECHNICAL_REQ,
CODING_CONVENTIONS and TESTING: first argument routing, output, configuration,
help and isolation; then maintainability, API boundaries, dependency reuse and
regression coverage. No database policies or SQL calls were added to the CLI.

| Finding | Priority | Correction / evidence |
|---|---|---|
| JSON mode needed explicit empty/Unicode/newline content checks in addition to envelope preservation. | Low | Expanded S5-004; final 658-case run passed. |
| Read dispatch used an implicit fallback for the info command. | Low | Made info dispatch explicit and reject unsupported internal commands; regression passed. |

Documentation passes review README, DEVELOPMENT, TEST_SPECIFICATION, AGENTS,
ARKKAN_HANDOVER and the Stage 4/5 reports against the actual commands, source,
JUnit results and owner's sequencing decision. Content review corrects stale
Stage 5 authorization and Stage 4 push status. Quality review checks command
examples, links, progress tables and separation of package completion from
stage acceptance. No unresolved material WP1 finding remains.

## 4. WP2 execution evidence and audits

- Date: 2026-11-26, development checkout on the owner's Mac; existing Python
  3.12.10 / pytest 9.1.1 virtual environment.
- Tested source checkpoint: `6b591c7677f8428220c40caab3eca86c2dd5def8`.
  Tests ran before committing; the source/test checkpoint contains those exact
  files. Subsequent documentation edits do not change the tested implementation.
- Four commands added: `resource add`, `resource update`, `type add`, `type update`.

```bash
.venv/bin/python -m pytest tests/unit -q --junitxml=/private/tmp/arkkan-stage5-wp2.xml
```

**Result: 803 passed in 1.51 seconds; zero failures, errors or skips.** The run
includes 658 prior cases and 145 new WP2 cases (S5-009–018), for 211 CLI cases.
The initial 800-case run passed; audit added three failure/ordering cases.
The installed executable also successfully ran `resource add --help` and
`type update --help`, without a database connection.

JUnit artifact: `/private/tmp/arkkan-stage5-wp2.xml`; temporary files may be
removed by host cleanup. SHA-256: `4b9cf7677ef3efcce7bd6ce9de9d0804276e083f456a3f817e500040da95ddba`.

| IDs | Verified scope | Outcome |
|---|---|---|
| S5-009–011 | Creation defaults, literal values, UTF-8 file/stdin input, preservation and local errors | Passed |
| S5-012–014 | Metadata combinations, null clearing, type operations and invalid syntax | Passed |
| S5-015–016 | Help, human/JSON output, API error envelopes and exit codes | Passed |
| S5-017–018 | Sanitized read failures and syntax rejection before stdin consumption | Passed |

Source pass 1 checked command/API contracts, input preservation, omission versus
null, option combinations and safe errors against TECHNICAL_REQ's CLI section.
It identified a low-priority coverage gap for simulated permission failures and
syntax rejection before stdin consumption; S5-017–018 now cover these paths.
Source pass 2 checked maintainability, typed helpers, public API use, dependency
reuse and prior read-command regressions. Input branching was made clearer;
no unresolved material finding remains. The final unit run includes corrections.

README, DEVELOPMENT, TEST_SPECIFICATION, ARKKAN_HANDOVER and this report completed
content/compliance and separate quality audits. Checks compared actual source,
help, Git revision and JUnit evidence with documentation, verified preservation
of historical results, and distinguished eight implemented commands from pending operations.
The stale WP1 push status and pending creation/update descriptions are updated.
No real database authorization or persistence is inferred from unit doubles.
The quality pass verified command examples, local link targets, test names and
cross-document progress consistency; no additional material finding remained.

## 5. WP3 execution evidence and audits

- Date: 2026-11-26, development checkout on the owner's Mac; existing Python
  3.12.10 / pytest 9.1.1 virtual environment.
- Tested source checkpoint: `dd0bff247b4b9ed7f3a29526fcfbb57c2010e13a`.
  Tests ran before commit; the checkpoint contains the tested source and tests.
- Eight lifecycle/deletion commands complete all 16 CLI mappings. No SQL,
  dependencies, configuration or public Python API contracts changed.

```bash
.venv/bin/python -m pytest tests/unit -q --junitxml=/private/tmp/arkkan-stage5-wp3.xml
.venv/bin/arkkan resource state --help
```

**Final result: 931 passed in 1.77 seconds; no failures, errors or skips.** This
includes 803 prior cases and 128 WP3 cases under S5-019–024 (339 CLI cases total).
The initial run passed 923 cases; review added eight force-scope checks for
previously implemented commands. Installed executable help succeeded without a
database connection and describes the restricted force behavior.

JUnit artifact: `/private/tmp/arkkan-stage5-wp3.xml`; host cleanup may remove it.
SHA-256: `50e03d23644be33ce207ba7a6e54248d05a4e39be4f19b3fb746b496c9afba08`.

| IDs | Verified scope | Outcome |
|---|---|---|
| S5-019–020 | Eight exact API mappings, literal inputs, human/JSON output and error streams | Passed |
| S5-021–022 | Boolean force/default behavior and successful zero counts | Passed |
| S5-023–024 | Invalid syntax/options before calls, force exclusion on all other commands and help | Passed |

Source audit 1 compared command mappings and response fields with TECHNICAL_REQ
CLI and Admin API sections, including `changed_count` for bulk state operations.
It found a low-priority coverage gap: force rejection was checked only for new
commands. Eight cases now verify rejection on the earlier commands as well.
Source audit 2 checked explicit dispatch, public API boundaries, typed helpers,
shared output handling, independent expected test values and regression coverage.
No additional material finding remained. The final run includes the correction.

README, DEVELOPMENT, TEST_SPECIFICATION, ARKKAN_HANDOVER and this report completed
separate content/compliance and quality audits. Content checks reconciled command
syntax, policy descriptions, test names/counts, JUnit evidence, Git checkpoints
and pending work with requirements and implementation. The revised files retain
historical results and the owner's deferred acceptance. Quality checks cover
readability, examples, local links and consistent progress/pickup guidance.
Minor wording/wrapping corrections clarify the overview and WP2 push status;
no material content discrepancy or unresolved quality finding remained.
Database CLI validation was not executed in WP3; WP4 evidence follows.

## 6. WP4 execution evidence and audits

- Date: 2026-11-26, development and staging checkouts on the owner's Mac.
- Python 3.12.10 / pytest 9.1.1; real installed executable and Psycopg/PostgreSQL.
- Initial test checkpoint: `c1db1fcaaa724e305bea1ed2dc6cc0892bbcc85d`.
- Final audited checkpoint: `a226b9e715286b0aa19b857c95333e42a92e7347`.
- No application source, SQL, configuration or dependency changes were required.

Development regression: `.venv/bin/python -m pytest tests/unit -q --junitxml=/private/tmp/arkkan-stage5-wp4-unit.xml`
passed **931 cases in 1.72 seconds**. Staging's editable installation was refreshed
with `.venv/bin/python -m pip install --no-deps --no-build-isolation -e .`.

Initial staging run at `c1db1fc`:

```bash
.venv/bin/python -m pytest tests/e2e -q --junitxml=/private/tmp/arkkan-stage5-wp4-e2e.xml
```

**5 passed in 337.77 seconds**, no failures, errors or skips. Tests exercise all
16 command mappings with actual database calls, both roles and password-file
credentials. Each executable invocation is preceded by staging verification;
child processes use explicit target settings, with no API/driver doubles.
Fixtures reset only known application objects/roles using the existing guarded
helpers. Temporary credentials are protected, checked for preservation and removed.

Final staging run at `a226b9e`:

```bash
.venv/bin/python -m pytest tests/unit tests/e2e -q --junitxml=/private/tmp/arkkan-stage5-wp4-final.xml
```

**936 passed in 345.40 seconds**, comprising 931 unit cases and all five e2e
cases; zero failures, errors or skips. The post-run command
`.venv/bin/python scripts/manage_environment.py check` passed, and staging
remains clean at the tested revision. Earlier-stage integration tests were not
rerun in WP4; cumulative unit/integration/e2e regression remains WP5.

| IDs | Scope | Final outcome |
|---|---|---|
| S5-025 | Literal identifiers, file/stdin/empty content, all reads for both roles, metadata updates | Passed |
| S5-026 | Lifecycle/deletion, force restrictions, atomic rejections, retained definitions and counts | Passed |
| S5-027 | Reader denial for all 12 writes, human/JSON errors, missing-password failure/recovery | Passed |
| S5-028 | Local UTF-8/syntax failure, sanitized errors and data preservation | Passed |
| S5-029 | Injected database failure, rollback, diagnostic sanitization and recovery | Passed |

Source audit 1 checked command coverage, real persistence, role/password-file
behavior, binary input/output and staging isolation. It identified insufficient
proof that metadata clearing changed stored values: `93a5286` sets nonempty
metadata, verifies stored empty strings and revised version information, then
verifies cleared nulls.
Source audit 2 checked helper reuse, cleanup, timeout behavior, credential handling
and maintainability. `a226b9e` compares password-file hashes so assertion failures
cannot print credential contents. All five cases passed again after this fixture
correction, which affects every case. No database policy or safety guard was bypassed.

README, DEVELOPMENT, TEST_SPECIFICATION, ARKKAN_HANDOVER and this report each
received full-file content/compliance and separate quality review passes.
Pass 1 compared the CLI requirements, test source, Git checkpoints and execution
evidence; it clarified historical pending-status wording and corrected the
metadata-audit description to match the actual assertions. Pass 2 checked
commands, test names, local link paths, progress/pickup consistency and readability.
It distinguished Stage 4 regression instructions from Stage 5's added e2e suite
and made S5-025's version-information coverage precise. Final results and
post-run status were rechecked against JUnit and command output. Baseline diffs
preserve historical evidence and owner decisions. No unresolved material finding
remains; stage acceptance and the validation limits below remain unchanged.

Supplementary JUnit files may be removed by host cleanup. SHA-256:

- Development unit: `6447854216d0be098bb15e584398398b9c94a500f11815baebb8c9c1a113da2b`.
- Initial e2e: `5705828b8290ed2fc7a9aee9a7abd115760d6cd01df8c7b73fc1d13870e97d70`.
- Final unit/e2e: `14df1648690436b273a445e4a0c0940aeb252a1b63d2b6e6409e77a687802527`.

## 7. Remaining validation and limitations

WP1–WP3 used local doubles; WP4 adds actual CLI database evidence separately.
The existing Stage 4 integration evidence is not relabeled as CLI evidence.

All command mappings are implemented. Prior-stage database regression and
cumulative CLI verification are planned in WP5. Stage 5 is not complete or ready for
acceptance. Stage 6 is not authorized. WP4 resets staging application fixtures;
development database contents were not changed. Linux execution and owner manual
validation are not established by these macOS tests.

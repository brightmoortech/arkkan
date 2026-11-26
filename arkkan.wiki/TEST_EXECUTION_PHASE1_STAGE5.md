# arkkan Test Execution Report

## Phase 1, Stage 5: CLI

**Status:** In progress; WP1 complete, WP2–WP6 pending. This report accumulates
actual evidence and will be finalized at Stage 5 closeout. Stage 4 acceptance
is deferred until the owner can test through the CLI. The owner explicitly
authorized Stage 5; no owner acceptance or manual test results are claimed.

## 1. Work packages

| Package | Scope | Status |
|---|---|---|
| WP1 | Installable executable, help, output/errors and four read commands | Complete; checkpoint `0489e93` |
| WP2 | Resource/type creation and metadata updates, UTF-8 file/stdin input and clearing | Pending |
| WP3 | Lifecycle/deletion commands; all 16 command mappings | Pending |
| WP4 | Real PostgreSQL CLI workflows, role authorization and password-file authentication | Pending |
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

## 3. Audits and corrections

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

## 4. Remaining validation and limitations

No PostgreSQL or CLI database tests were run in WP1. Public API doubles establish
routing and presentation only; real authentication, role authorization, database
failures and command workflows remain WP4 requirements. The existing Stage 4
integration evidence is not relabeled as CLI evidence.

Administration commands, content files/stdin and metadata clearing remain WP2;
lifecycle/deletion commands remain WP3. The `type` namespace currently supplies
help identifying its operations as pending. Prior-stage database regression is
planned in WP5. Stage 5 is not complete or ready for acceptance. Stage 6 is not
authorized. Staging and development database contents were not changed by WP1.

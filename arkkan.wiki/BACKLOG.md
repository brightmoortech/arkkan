# arkkan Backlog

## Purpose and maintenance

Record deferred improvements and their intended outcomes without changing approved requirements or authorizing implementation. Functional and Technical Requirements remain authoritative for existing commitments, phase boundaries, and acceptance criteria. This backlog is not a substitute for unresolved defects or unmet mandatory validation criteria.

Add an item when an improvement is identified and deferred; maintain its identifier, scope, source, and disposition as decisions change. Specify and authorize work before implementation. Record completed items only after validation. No delivery priority or implementation phase is assigned unless explicitly approved.

## Environment management

All entries below are deferred; none is implemented by this document.

| ID | Improvement | Intended outcome / proposed acceptance | Source |
|---|---|---|---|
| UX-01 | Distinguish expected operator action from an error. | Missing first-time credentials produce an `[ACTION REQUIRED]` message with paths, permissions and the next action. Return a nonzero exit code while setup is incomplete; do not create credentials or begin database provisioning. | Approved during staging provisioning; current utility reports `[ERROR]` after directory preparation. |
| UX-02 | Report progress during lengthy provisioning. | Provide meaningful progress and completion messages for validation, directory preparation, container provisioning, database readiness, authentication and identity verification. Preserve concise output on safe reruns and never disclose credentials. | Development setup completed successfully but displayed only a final success message after a noticeable wait. |
| UX-03 | Identify the conflicting resource in diagnostics. | Report the conflicting container name and configured host port when another container is configured to use the requested host port. Distinguish a configured Docker conflict from an active host listener where evidence permits. Preserve rejection behavior, including conflicts with stopped containers. | Initial development provisioning was blocked by the stopped automation environment's configured host port; additional Docker inspection was required. |
| UX-04 | Provide an informative verification summary. | Report which configuration, infrastructure, readiness, connectivity, authentication and environment identity checks succeeded or failed. Do not claim checks were performed if they were not; `check` remains read-only. | Both successful environment checks displayed only a final success message. |
| ENV-01 | Comprehensive solution health checks and structured health reports. | Define and validate health criteria and report structure in a future assignment; extend the environment management utility without duplicating its provisioning logic. | Technical Requirements, Environment Provisioning. |
| ENV-02 | Recovery diagnostics and controlled recovery routines. | Define supported recovery scenarios, protections, authorization and verification before implementation. Never silently delete persistent storage, overwrite credentials, or relabel an existing database. | Technical Requirements, Environment Provisioning and Data Architecture / Backup and Recovery. |

The basic manual database backup-and-restore procedure remains a local-development requirement under Technical Requirements; it is not deferred by ENV-02. Production recovery objectives and later phases remain governed by the existing Roadmap.

## Reusable workflow conventions

| ID | Improvement | Intended outcome / proposed acceptance | Source |
|---|---|---|---|
| UX-05 | Standardize workflow status terminology. | Reconcile status labels and their semantics when consolidating reusable generation, provisioning and initialization workflows into pyprojectgen. Preserve existing behavior until that future work is specified and authorized. | Deferred by project owner during WP3 dry-run review; no current status-label changes. |

## Phase 4: Production Readiness

| ID | Improvement | Intended outcome / proposed acceptance | Source |
|---|---|---|---|
| REC-01 | Database backup and recovery utilities. | Provide separate backup and restore scripts with an operator-specified backup destination. Default to dry run; require `--apply` to execute. Validate target environment and backup integrity, prevent unintended overwrites, and verify restoration. Specify and test selective data recovery without losing subsequent legitimate transactions, complete database recovery, and full-cluster disaster recovery including required roles and credentials. Keep utilities in arkkan; possible future extraction to a standalone toolbox is not authorized implementation work. Do not include operational maintenance utilities in pyprojectgen. | Project-owner decisions during Stage 2 recovery drill; Technical Requirements, Backup and Recovery and Phase 4 Roadmap. |

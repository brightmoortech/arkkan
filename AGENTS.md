# Repository Documentation Guide

## 1. Document Registry

Paths are relative to the repository root. The registry identifies each document's purpose and domain of authority; it does not replace the documents or the assigned task instructions.

| Document | Purpose and authority |
|---|---|
| [README.md](README.md) | User-facing project overview, installation, configuration, usage, and operational guidance as functionality becomes available. |
| [DEVELOPMENT.md](arkkan.wiki/DEVELOPMENT.md) | Contributor and maintainer guidance for development setup, configuration, and test execution. |
| [FUNCTIONAL_REQ.md](arkkan.wiki/FUNCTIONAL_REQ.md) | Authoritative functional requirements: resource behavior, lifecycle policies, and role capabilities. |
| [TECHNICAL_REQ.md](arkkan.wiki/TECHNICAL_REQ.md) | Authoritative technical requirements: architecture, schema, interfaces, security, deployment, implementation stages, and acceptance criteria. |
| [CODING_CONVENTIONS.md](arkkan.wiki/CODING_CONVENTIONS.md) | Approved coding conventions, API boundaries, diagnostics, and dependency management. |
| [TESTING.md](arkkan.wiki/TESTING.md) | Approved automated testing governance, isolation, execution, evidence, and acceptance rules. |
| [TEST_SPECIFICATION.md](arkkan.wiki/TEST_SPECIFICATION.md) | Test case definitions and traceability to requirements and acceptance criteria. |
| [TEST_EXECUTION_PHASE1_STAGE1.md](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE1.md) | Recorded test execution evidence for Phase 1, Stage 1; not a requirements source. |
| [TEST_EXECUTION_PHASE1_STAGE2.md](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE2.md) | Recorded test execution evidence and closeout status for Phase 1, Stage 2; not a requirements source. |
| [TEST_EXECUTION_PHASE1_STAGE3.md](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE3.md) | Recorded test execution evidence, review findings and closeout status for Phase 1, Stage 3; not a requirements source. |
| [TEST_EXECUTION_PHASE1_STAGE4.md](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE4.md) | Recorded test execution evidence, review findings, limitations and acceptance checkpoint for Phase 1, Stage 4; not a requirements source. |
| [TEST_EXECUTION_PHASE1_STAGE5.md](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE5.md) | Final Stage 5 CLI execution evidence, work-package status, audits, limitations and acceptance checkpoint; not a requirements source. |
| [DOCUMENT_GOVERNANCE.md](arkkan.wiki/DOCUMENT_GOVERNANCE.md) | Governs authorized document creation, modification, review, auditing, and delivery. |
| [BACKLOG.md](arkkan.wiki/BACKLOG.md) | Deferred improvements and proposed outcomes; update when items are identified, approved, deferred, or validated. Not a source of implementation authorization. |
| [AGENTS.md](AGENTS.md) | Repository documentation registry, reading guidance, and maintenance triggers. |
| [ARKKAN_HANDOVER.md](ARKKAN_HANDOVER.md) | Continuation snapshot through Stage 5 closeout: completed work, validation evidence, acceptance decision and resume guidance; not a requirements source or authorization. |

## 2. Document Reading Guidance

Select documents according to the assigned objective and scope. The following sequences identify relevant repository documents; read other applicable instructions and externally supplied governing documents as required by the task, including the Software Architectural Principles and LLM Clarification Process when applicable. For tasks involving document creation or modification, also read `DOCUMENT_GOVERNANCE.md` before making document changes. Do not infer authorization from this guide.

| Task | Reading guidance (in order) |
|---|---|
| Understand or use the project | `README.md`; applicable interface or operational sections in `TECHNICAL_REQ.md` if further detail is needed. |
| Analyze requirements or design | `README.md`, `FUNCTIONAL_REQ.md`, `TECHNICAL_REQ.md`; applicable conventions and testing governance. |
| Implement or maintain software | `FUNCTIONAL_REQ.md`, `TECHNICAL_REQ.md`, `CODING_CONVENTIONS.md`, `TESTING.md`, `DEVELOPMENT.md`, `TEST_SPECIFICATION.md`; applicable test execution reports. |
| Design, execute, or review tests | `FUNCTIONAL_REQ.md`, `TECHNICAL_REQ.md`, `TESTING.md`, `CODING_CONVENTIONS.md`, `TEST_SPECIFICATION.md`, `DEVELOPMENT.md`; applicable test execution reports. |
| Evaluate deferred improvements or prepare future work | `BACKLOG.md`; applicable functional and technical requirements and governing documents. |
| Create, modify, or review documentation | `DOCUMENT_GOVERNANCE.md`, the target document, and its applicable authoritative sources from the registry. |

## 3. Maintenance Rules

- Update the registry when a project document is added, removed, renamed, relocated, or its purpose or authority changes. Include new stage test execution reports as they are created.
- Update reading guidance when document dependencies or applicability change.
- Do not update this guide merely because the content of a registered document changes without affecting its purpose, authority, location, or reading guidance.
- Follow the applicable authorization process and `DOCUMENT_GOVERNANCE.md` before modifying this guide.

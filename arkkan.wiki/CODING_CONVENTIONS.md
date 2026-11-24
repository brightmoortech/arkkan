# arkkan Coding Conventions

## 1. Purpose and Scope

Define the coding conventions for `arkkan`. Follow `FUNCTIONAL_REQ.md`, `TECHNICAL_REQ.md`, the Software Architectural Principles, and the Software Developer prompt. These conventions do not change approved requirements, API contracts, or implementation stage boundaries. Follow `TESTING.md` for automated testing governance.

## 2. Coding Style

- Follow PEP 8 for Python code.
- Use `snake_case` for Python function and variable names and PostgreSQL identifiers. Use `UPPER_CASE` for Python constants. Use four-space indentation and follow PEP 8 class naming where classes are justified.
- Use descriptive names rather than unnecessary abbreviations. Preserve explicitly specified identifiers and interface names.

## 3. Python Type Annotations

- Annotate all function parameters and return values, including `None` returns.
- Prefer native Python type annotations where practical.
- Do not introduce an additional runtime type-checking framework. Type annotations do not replace required input validation.

## 4. Function Design

- Give each function a clearly defined responsibility.
- Prefer explicit parameters over global variables.
- Avoid mutable default arguments.
- Use classes only when justified by state management or encapsulation.
- Document public functions concisely; use Python docstrings as specified in Section 5.

## 5. Code Comments and Documentation

- Explain non-obvious logic, constraints, and design decisions in comments. Explain why rather than restating what the code does.
- Use concise public Python function docstrings describing purpose, parameters, return values, and error behavior.
- Remove obsolete comments when modifying the associated code.
- Avoid excessive documentation of self-explanatory code.

## 6. Error Handling

- Follow the common JSON response contract in `TECHNICAL_REQ.md` for public API operations. Translate database errors at the Python API boundary as specified there.
- Catch specific exceptions rather than using blanket exception handlers. Do not silently suppress errors.
- Provide concise, actionable error messages without credentials, sensitive content, or raw SQL diagnostics.
- Only executable entry points, such as the CLI and initialization script, may terminate the process. Reusable library functions must return or propagate errors according to their contracts.

## 7. PostgreSQL Coding Conventions

- Use uppercase SQL keywords and lowercase identifiers.
- Explicitly qualify database object references with their schema names where applicable. Follow the required safe `search_path` for privileged functions.
- Use explicit column names rather than `SELECT *`.
- Use parameterized SQL queries in Python.
- Give SQL functions clearly defined responsibilities. Enforce resource business rules in PostgreSQL, not in the Python API or CLI.
- Maintain SQL migrations in numbered files ordered by execution dependency. Follow the initialization and migration requirements in `TECHNICAL_REQ.md`.
- Every completed public PostgreSQL API function must construct its response envelope through `arkkan.api_response(operation_name, result, data, reason)`. Supply the operation-specific JSONB payload for success or a concise, safe reason for error; do not construct the envelope independently or return raw database diagnostics. Test the exact operation name and response shape at the public API boundary. An invalid internal helper call is a programming error, not an ordinary API error response.

## 8. Logging and Diagnostics

- Use Python's standard `logging` module for logging.
- Send diagnostic messages to standard error. Preserve standard output for command results according to the CLI contract.
- Make logging configurable by severity.
- Never log credentials or prompt content. Protect sensitive information in diagnostic messages.
- Defer database audit logging to Phase 3 as specified in `TECHNICAL_REQ.md`. Diagnostic logging does not introduce Phase 3 audit functionality.

## 9. Dependency Management

- Pin all direct and transitive dependencies to exact versions, including applicable build, runtime, development, and testing dependencies.
- Separate runtime dependencies from development and testing dependencies.
- Prefer the Python standard library where practical.
- Introduce third-party dependencies only when justified. Obtain user approval before adding or upgrading dependencies.

## 10. API Boundaries and Encapsulation

### Python

- The supported public Python API consists only of the functions defined in `TECHNICAL_REQ.md`; executable entry points are not resource API functions. Explicitly declare public exports using `__all__` at the public API boundary.
- Distinguish internal functions from public API functions by prefixing internal function names with `_`. Use separate internal modules where appropriate; do not introduce unnecessary modules solely for separation.
- Python naming and export conventions identify the supported interface; they are not security controls.

### PostgreSQL

- Expose specified public SQL functions through the `arkkan_api` schema, with execution permissions restricted to the appropriate roles.
- Keep internal helper functions outside `arkkan_api` and restrict their execution permissions according to `TECHNICAL_REQ.md`. Ordinary API roles must not bypass PostgreSQL policy enforcement.

### CLI and Compatibility

- The CLI accesses resource functionality exclusively through the public Python API. It does not access tables directly or duplicate resource policies. Local argument parsing and input/output handling remain CLI responsibilities.
- Preserve public API contracts unless explicitly authorized to change them. Internal functions may be refactored within authorized scope without changing those contracts.

# arkkan

## Overview

`arkkan` is a centralized repository for versioned prompt resources, designed
for authorized applications to discover and retrieve reusable prompt content.
Consuming applications assemble resources into prompts; `arkkan` does not
assemble prompts.

**Current status:** Phase 1, Stage 2 (Database Foundation) was accepted on
November 24, 2026. Stage 3 implements all 16 PostgreSQL API operations and their
role permissions and was accepted on November 25, 2026. See the
[Stage 3 execution report](arkkan.wiki/TEST_EXECUTION_PHASE1_STAGE3.md) for validation
evidence. Stage 4 is in progress: all 16 Python API functions are implemented
and unit-tested. Stage 4 PostgreSQL integration validation and the CLI remain
pending.

For development setup and automated testing, see [DEVELOPMENT.md](arkkan.wiki/DEVELOPMENT.md).

## Features

## System Requirements

## Installation

## Configuration

## Initialization

## Getting Started

## CLI Reference

## Python API Reference

The available read functions are exported from `arkkan`:

```python
from arkkan import (
    get_resource_content,
    get_resource_info,
    get_resource_version_default,
    list_resources_matching_type,
)

response = get_resource_content("example")  # Default version only.
response = get_resource_content("example", "v1")  # Strict version lookup.
response = get_resource_content("example", "v1", "version_priority")
```

Set `PGDATABASE` and `PGUSER` in the process environment, with `PGHOST`, `PGPORT`
and `PGPASSFILE` as needed. Use an authorized `arkkan_user` or `arkkan_admin`
account and its protected client password file. The Python API does not load
`.env` automatically. The target database must already have the Stage 3 SQL API
initialized; importing the package does not initialize or connect to it.

Functions return the decoded common JSON response defined in
[Technical Requirements](arkkan.wiki/TECHNICAL_REQ.md#common-api-contracts).
Check `response["result"]` before accessing `response["data"]`; errors include
`reason`. Content retrieval also accepts `strict` and `default_priority` modes.
Omitting `version` selects the default; explicitly passing `None` is invalid.
Supplying `mode` requires `version`. Slugs and versions are passed unchanged.
Unsupported Python argument types return an error response; malformed Python
call signatures (missing, extra, duplicate or unknown arguments) raise `TypeError`.

`get_resource_info(slug)` returns metadata and all version states without content;
`get_resource_version_default(slug)` identifies the default version;
`list_resources_matching_type(type_slug)` returns resource metadata for a type,
including resources with no versions. See the technical requirements for full
response payloads and PostgreSQL selection policies. Actual database integration
validation of these Python wrappers is pending; the examples are usage guidance,
not recorded database test results.

Resource and resource-type administration functions are also exported from
`arkkan` and require `arkkan_admin` permissions, enforced by PostgreSQL:

```python
from arkkan import (
    add_resource, update_resource,
    add_resource_type, update_resource_type, delete_resource_type,
)

response = add_resource("example", "v1", type_slug="task", content="Prompt text")
response = update_resource("example", {"description": None})
response = update_resource("example", {"version_info": "Revised"}, version="v1")
```

`add_resource` defaults to empty content and the `disabled` state. Supply a type
for a new resource; PostgreSQL validates existing resources and type matching.
`update_resource` takes a dictionary of string keys and string/null values:
omitted fields remain unchanged, `None` clears a field, and `""` stores an empty
string. Supply `version` when changing `version_info`; PostgreSQL rejects unknown
keys, empty changes and invalid version combinations. The caller's dictionary is
not modified. `add_resource_type(slug, description=None)` creates a custom type;
`update_resource_type(slug, description)` sets or clears its description;
`delete_resource_type(slug)` requests deletion of an unused custom type.

These functions use the same configuration and response/error conventions as
reads. They call the existing SQL API; protected-type, immutability and lifecycle
rules are enforced there. Their PostgreSQL integration validation is pending.

Lifecycle and deletion functions use the same response conventions and require
`arkkan_admin` permissions:

| Function | Purpose |
|---|---|
| `set_resource_state(slug, version, target_state, force=False)` | Change one version; force permits default removal without replacement only. |
| `set_resource_state_all(slug, target_state)` | Change every version atomically, subject to transition and default policies. |
| `set_resource_state_all_with_guard(slug, source_state, target_state)` | Change versions matching the source state atomically. |
| `delete_resource_version(slug, version)` | Delete one obsolete version, keeping its resource. |
| `delete_resource_version_all(slug)` | Delete a resource's obsolete versions, keeping its definition. |
| `clean_up()` | Delete obsolete versions across all resources, keeping definitions. |
| `delete_resource(slug)` | Delete a resource only if empty or all its versions are obsolete. |

Import these functions from `arkkan`. Bulk state changes have no force option.
Supply an actual boolean for `force`, not a string or integer. Explicit `None`
is passed as SQL NULL and rejected by PostgreSQL. PostgreSQL enforces lifecycle,
default-preservation and deletion rules; these wrappers do not duplicate them.
Their actual PostgreSQL integration validation remains pending in WP5.

## Examples

## Security and Access Management

## Backup and Recovery

## Troubleshooting

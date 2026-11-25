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
evidence. Stage 4 is in progress: the Python API foundation and four read
functions are implemented and unit-tested. Python administration functions,
Stage 4 PostgreSQL integration validation, and the CLI remain pending.

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

## Examples

## Security and Access Management

## Backup and Recovery

## Troubleshooting

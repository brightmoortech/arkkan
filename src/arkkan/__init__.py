"""Public Python interface to the arkkan PostgreSQL API."""

from arkkan._read import (
    get_resource_content,
    get_resource_info,
    get_resource_version_default,
    list_resources_matching_type,
)

__all__ = [
    "get_resource_content",
    "get_resource_info",
    "get_resource_version_default",
    "list_resources_matching_type",
]

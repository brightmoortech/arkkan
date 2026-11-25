"""Public Python interface to the arkkan PostgreSQL API."""

from arkkan._read import (
    get_resource_content,
    get_resource_info,
    get_resource_version_default,
    list_resources_matching_type,
)
from arkkan._write import (
    add_resource,
    add_resource_type,
    delete_resource_type,
    update_resource,
    update_resource_type,
)

__all__ = [
    "add_resource",
    "add_resource_type",
    "delete_resource_type",
    "get_resource_content",
    "get_resource_info",
    "get_resource_version_default",
    "list_resources_matching_type",
    "update_resource",
    "update_resource_type",
]

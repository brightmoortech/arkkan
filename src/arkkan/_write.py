"""Resource administration wrappers; PostgreSQL enforces business policies."""

from typing import Any

from psycopg.types.json import Jsonb

from arkkan._api import _call, _error_response


def _text_values_valid(parameters: tuple[object, ...]) -> bool:
    return all(value is None or isinstance(value, str) for value in parameters)


def _write_call(operation_name: str, parameters: tuple[object, ...]) -> dict[str, Any]:
    if not _text_values_valid(parameters):
        return _error_response(operation_name, "Text arguments must be strings or null.")
    return _call(operation_name, parameters)


def add_resource(
    slug: str,
    version: str,
    type_slug: str | None = None,
    name: str | None = None,
    description: str | None = None,
    content: str = "",
    version_info: str | None = None,
    state: str = "disabled",
) -> dict[str, Any]:
    """Create a version and, if needed, its resource; return common JSON.

    Supply type_slug for a new resource. name/description describe new resources;
    content is immutable, version_info is editable, and state defaults to disabled.
    PostgreSQL enforces duplicates, type matching and default replacement.
    Invalid inputs, denied access and database failures return error responses.
    Malformed Python call signatures raise TypeError.
    """
    return _write_call("add_resource", (
        slug, version, type_slug, name, description, content, version_info, state,
    ))


def update_resource(
    slug: str, changes: dict[str, str | None], version: str | None = None,
) -> dict[str, Any]:
    """Update metadata through common JSON; omitted keys remain unchanged.

    changes supplies name, description or version_info; None clears a field.
    Supply version exactly when updating version_info. PostgreSQL validates keys
    and targets. Invalid inputs, denied access and database failures return error
    responses. Malformed Python call signatures raise TypeError.
    """
    if changes is not None and (
        not isinstance(changes, dict)
        or any(
            not isinstance(key, str)
            or (value is not None and not isinstance(value, str))
            for key, value in changes.items()
        )
    ):
        return _error_response(
            "update_resource",
            "Changes must be an object with string keys and string or null values.",
        )
    if not _text_values_valid((slug, version)):
        return _error_response(
            "update_resource", "Text arguments must be strings or null.",
        )
    # Explicit SQL NULL stays NULL; JSON null values inside an object clear fields.
    payload = None if changes is None else Jsonb(changes.copy())
    return _call("update_resource", (slug, payload, version))


def add_resource_type(slug: str, description: str | None = None) -> dict[str, Any]:
    """Create a custom type with optional description; return common JSON.

    Invalid inputs, duplicate types, denied access and database failures return
    error responses. Malformed Python call signatures raise TypeError.
    """
    return _write_call("add_resource_type", (slug, description))


def update_resource_type(slug: str, description: str | None) -> dict[str, Any]:
    """Set a type's description, or clear it with None; return common JSON.

    Invalid/unknown types, denied access and database failures return error
    responses. Malformed Python call signatures raise TypeError.
    """
    return _write_call("update_resource_type", (slug, description))


def delete_resource_type(slug: str) -> dict[str, Any]:
    """Delete an unused custom type identified by slug; return common JSON.

    PostgreSQL rejects protected/referenced types. Invalid/unknown types, denied
    access and database failures return error responses. Malformed Python call
    signatures raise TypeError.
    """
    return _write_call("delete_resource_type", (slug,))

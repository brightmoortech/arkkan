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


def delete_resource_version(slug: str, version: str) -> dict[str, Any]:
    """Delete one obsolete version, preserving its resource; return common JSON.

    PostgreSQL checks slug/version and deletion eligibility. Invalid inputs,
    denied access and database failures return errors; malformed calls raise TypeError.
    """
    return _write_call("delete_resource_version", (slug, version))


def delete_resource_version_all(slug: str) -> dict[str, Any]:
    """Delete a resource's obsolete versions; return common JSON with a count.

    PostgreSQL preserves the definition and permits zero deletions. Invalid
    inputs, denied access and database failures return errors; malformed calls
    raise TypeError.
    """
    return _write_call("delete_resource_version_all", (slug,))


def clean_up() -> dict[str, Any]:
    """Delete all obsolete versions atomically, preserving resource definitions.

    Return common JSON with a deletion count, including zero. Denied access and
    database failures return errors; malformed calls raise TypeError.
    """
    return _call("clean_up", ())


def delete_resource(slug: str) -> dict[str, Any]:
    """Delete an empty or entirely obsolete resource; return common JSON.

    PostgreSQL enforces eligibility and preserves the type. Invalid inputs,
    denied access and database failures return errors; malformed calls raise TypeError.
    """
    return _write_call("delete_resource", (slug,))


def set_resource_state(
    slug: str, version: str, target_state: str, force: bool = False,
) -> dict[str, Any]:
    """Change one version's state; return common JSON.

    force permits removing a default without replacement, not other invalid
    transitions. PostgreSQL enforces policy. Invalid inputs, denied access and
    database failures return errors; malformed calls raise TypeError.
    """
    operation = "set_resource_state"
    if not _text_values_valid((slug, version, target_state)):
        return _error_response(operation, "Text arguments must be strings or null.")
    if force is not None and not isinstance(force, bool):
        return _error_response(operation, "Force must be a boolean or null.")
    return _call(operation, (slug, version, target_state, force))


def set_resource_state_all(slug: str, target_state: str) -> dict[str, Any]:
    """Change all versions to target_state atomically; return common JSON.

    PostgreSQL validates every transition and default policy; there is no force
    option. Invalid inputs, denied access and database failures return errors;
    malformed calls raise TypeError. Empty resources may return a zero count.
    """
    return _write_call("set_resource_state_all", (slug, target_state))


def set_resource_state_all_with_guard(
    slug: str, source_state: str, target_state: str,
) -> dict[str, Any]:
    """Change versions matching source_state atomically; return common JSON.

    PostgreSQL validates transitions and default policy; there is no force
    option. Invalid inputs, denied access and database failures return errors;
    malformed calls raise TypeError. No matching versions may return a zero count.
    """
    return _write_call(
        "set_resource_state_all_with_guard", (slug, source_state, target_state),
    )

"""Read wrappers; PostgreSQL owns selection, validation and authorization."""

from typing import Any

from arkkan._api import _call, _error_response


class _Omitted:
    """Distinguish an absent argument from an explicitly supplied SQL NULL."""


_OMITTED = _Omitted()


def _read_call(
    operation_name: str, parameters: tuple[object, ...],
) -> dict[str, Any]:
    # Do not allow driver adaptation to turn Python numbers, booleans or
    # containers into a different SQL argument type. SQL validates text values.
    if any(value is not None and not isinstance(value, str) for value in parameters):
        return _error_response(operation_name, "Read arguments must be strings or null.")
    return _call(operation_name, parameters)


def get_resource_content(
    slug: str,
    version: str | None | _Omitted = _OMITTED,
    mode: str | None | _Omitted = _OMITTED,
) -> dict[str, Any]:
    """Return content through the common decoded JSON response.

    Supply only slug for default retrieval, slug/version for strict retrieval,
    or all three arguments for strict, version_priority or default_priority.
    Explicit None is sent as SQL NULL, not treated as an omitted argument.
    Invalid values, unavailable content and database failures return an error
    response. Supplying mode without version returns an error before connecting.
    Malformed Python call signatures raise TypeError.
    """
    operation_name = "get_resource_content"
    if version is _OMITTED:
        if mode is not _OMITTED:
            return _error_response(operation_name, "Supply version when supplying mode.")
        return _read_call(operation_name, (slug,))
    if mode is _OMITTED:
        return _read_call(operation_name, (slug, version))
    return _read_call(operation_name, (slug, version, mode))


def list_resources_matching_type(type_slug: str) -> dict[str, Any]:
    """Return resource metadata for type_slug in the common JSON response.

    Includes resources with no versions; an empty list is a successful result.
    Invalid/unknown types and database failures return an error response.
    Malformed Python call signatures raise TypeError.
    """
    return _read_call("list_resources_matching_type", (type_slug,))


def get_resource_version_default(slug: str) -> dict[str, Any]:
    """Return slug's default version identifier in the common JSON response.

    Invalid slugs, absent defaults and database failures return an error response.
    Malformed Python call signatures raise TypeError.
    """
    return _read_call("get_resource_version_default", (slug,))


def get_resource_info(slug: str) -> dict[str, Any]:
    """Return slug's metadata and all version states in the common JSON response.

    Content is excluded. Invalid/unknown slugs and database failures return an
    error response. Malformed Python call signatures raise TypeError.
    """
    return _read_call("get_resource_info", (slug,))

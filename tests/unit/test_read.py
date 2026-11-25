"""S4-010–016: public read wrappers, without PostgreSQL connections."""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

import arkkan

_READ_NAMES = (
    "get_resource_content", "get_resource_info",
    "get_resource_version_default", "list_resources_matching_type",
)


@pytest.fixture
def call(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    execution = MagicMock()
    monkeypatch.setattr("arkkan._read._call", execution)
    return execution


def test_s4_010_public_exports() -> None:
    assert set(arkkan.__all__) == set(_READ_NAMES)
    assert len(arkkan.__all__) == len(_READ_NAMES)
    for name in arkkan.__all__:
        assert callable(getattr(arkkan, name))
        assert getattr(arkkan, name).__doc__


@pytest.mark.parametrize("name", _READ_NAMES)
@pytest.mark.parametrize("value", [" Mixed ' ; -- \u2603 ", "", " \t", None])
def test_s4_011_read_mapping(call: MagicMock, name: str, value: Any) -> None:
    result = getattr(arkkan, name)(value)
    call.assert_called_once_with(name, (value,))
    assert result is call.return_value
    call.reset_mock()
    parameter = "type_slug" if name == "list_resources_matching_type" else "slug"
    assert getattr(arkkan, name)(**{parameter: value}) is call.return_value
    call.assert_called_once_with(name, (value,))


@pytest.mark.parametrize(("arguments", "keywords", "expected"), [
    (("slug",), {}, ("slug",)),
    (("slug", "version"), {}, ("slug", "version")),
    (("slug", "version", "strict"), {}, ("slug", "version", "strict")),
    (("slug",), {"version": "v", "mode": "version_priority"},
     ("slug", "v", "version_priority")),
    ((), {"slug": "s", "version": "v", "mode": "default_priority"},
     ("s", "v", "default_priority")),
    (("slug", None), {}, ("slug", None)),
    (("slug", ""), {}, ("slug", "")),
    (("slug", " \t"), {}, ("slug", " \t")),
    (("slug", "v", None), {}, ("slug", "v", None)),
    (("slug", None, "version_priority"), {}, ("slug", None, "version_priority")),
    (("slug", "v", "UNKNOWN"), {}, ("slug", "v", "UNKNOWN")),
])
def test_s4_012_content_call_forms(
    call: MagicMock, arguments: tuple, keywords: dict, expected: tuple,
) -> None:
    result = arkkan.get_resource_content(*arguments, **keywords)
    call.assert_called_once_with("get_resource_content", expected)
    assert result is call.return_value


@pytest.mark.parametrize("mode", ["strict", "version_priority", None, ""])
def test_s4_013_mode_requires_version(call: MagicMock, mode: Any) -> None:
    response = arkkan.get_resource_content("slug", mode=mode)
    assert response == {
        "operation_name": "get_resource_content", "message_type": "response",
        "result": "error", "reason": "Supply version when supplying mode.",
    }
    call.assert_not_called()


@pytest.mark.parametrize("name", _READ_NAMES)
@pytest.mark.parametrize("value", [True, 123, 1.5, b"SECRET", ["SECRET"], {"SECRET": 1}])
def test_s4_014_invalid_python_types(
    call: MagicMock, name: str, value: Any,
) -> None:
    response = getattr(arkkan, name)(value)
    assert response == {
        "operation_name": name, "message_type": "response", "result": "error",
        "reason": "Read arguments must be strings or null.",
    }
    call.assert_not_called()
    if name == "get_resource_content":
        assert arkkan.get_resource_content("slug", value) == response
        assert arkkan.get_resource_content("slug", "v", value) == response
        call.assert_not_called()


@pytest.mark.parametrize("name", _READ_NAMES)
@pytest.mark.parametrize("result", ["success", "error"])
def test_s4_015_response_passthrough(
    call: MagicMock, name: str, result: str,
) -> None:
    payloads = {
        "get_resource_content": {
            "slug": "s", "version": "selected-default",
            "state": "enabled_default", "content": "",
        },
        "list_resources_matching_type": [],
        "get_resource_version_default": {"slug": "s", "version": "v"},
        "get_resource_info": {
            "slug": "s", "name": None, "description": None,
            "type_slug": "task", "versions": [],
        },
    }
    response = {"operation_name": name, "message_type": "response", "result": result}
    response.update({"data": payloads[name]} if result == "success"
                    else {"reason": "Requested resource version is unavailable."})
    call.return_value = response
    assert getattr(arkkan, name)("s") is response
    call.assert_called_once_with(name, ("s",))


@pytest.mark.parametrize("name", _READ_NAMES)
@pytest.mark.parametrize("malformation", ["missing", "excess", "unknown", "duplicate"])
def test_s4_016_malformed_call(
    call: MagicMock, name: str, malformation: str,
) -> None:
    function: Callable[..., dict[str, Any]] = getattr(arkkan, name)
    parameter = "type_slug" if name == "list_resources_matching_type" else "slug"
    with pytest.raises(TypeError):
        if malformation == "missing":
            function()
        elif malformation == "excess":
            function("s", "v", "strict", "extra")
        elif malformation == "unknown":
            function("s", unknown="value")
        else:
            function("s", **{parameter: "duplicate"})
    call.assert_not_called()

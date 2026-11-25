"""S4-017–023: administration wrappers with no database connections."""

import json
from typing import Any
from unittest.mock import MagicMock

from psycopg.types.json import Jsonb, JsonbDumper
import pytest

import arkkan

_WRITE_NAMES = (
    "add_resource", "update_resource", "add_resource_type",
    "update_resource_type", "delete_resource_type",
)


@pytest.fixture
def call(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    execution = MagicMock()
    monkeypatch.setattr("arkkan._write._call", execution)
    return execution


def test_s4_017_public_exports() -> None:
    assert set(arkkan.__all__) == set(_WRITE_NAMES) | {
        "get_resource_content", "get_resource_info",
        "get_resource_version_default", "list_resources_matching_type",
    }
    assert len(arkkan.__all__) == 9
    for name in _WRITE_NAMES:
        assert callable(getattr(arkkan, name))
        assert getattr(arkkan, name).__doc__


@pytest.mark.parametrize(("name", "arguments", "keywords", "expected"), [
    ("add_resource_type", (" custom ",), {}, (" custom ", None)),
    ("add_resource_type", (), {"slug": "s", "description": ""}, ("s", "")),
    ("add_resource_type", ("s", "\u2603"), {}, ("s", "\u2603")),
    ("update_resource_type", ("task", None), {}, ("task", None)),
    ("update_resource_type", (), {"slug": "s", "description": "new"}, ("s", "new")),
    ("update_resource_type", ("s", ""), {}, ("s", "")),
    ("delete_resource_type", ("task",), {}, ("task",)),
    ("delete_resource_type", (), {"slug": "s"}, ("s",)),
    ("add_resource", ("s", "v"), {}, ("s", "v", None, None, None, "", None, "disabled")),
    ("add_resource", (), {"slug": "s", "version": "v", "type_slug": "task",
                          "content": "' ; --\n\u2603", "state": "enabled_default"},
     ("s", "v", "task", None, None, "' ; --\n\u2603", None, "enabled_default")),
    ("add_resource", ("s", "v", "task", "name", "description", "content", "info", "enabled"),
     {}, ("s", "v", "task", "name", "description", "content", "info", "enabled")),
    ("add_resource", (None, " "), {"content": None, "state": "obsolete"},
     (None, " ", None, None, None, None, None, "obsolete")),
])
def test_s4_018_write_mapping(
    call: MagicMock, name: str, arguments: tuple, keywords: dict, expected: tuple,
) -> None:
    assert getattr(arkkan, name)(*arguments, **keywords) is call.return_value
    call.assert_called_once_with(name, expected)


@pytest.mark.parametrize("changes", [
    {"name": "new"}, {"description": None}, {"name": "", "description": None},
    {"version_info": "change \u2603"}, {"version_info": None},
    {"name": "new", "description": "desc", "version_info": "info"},
    {}, {"content": "immutable"}, None,
])
@pytest.mark.parametrize("version", [None, "v"])
def test_s4_019_json_changes(call: MagicMock, changes: Any, version: str | None) -> None:
    changes = None if changes is None else changes.copy()
    original = None if changes is None else changes.copy()
    assert arkkan.update_resource(" s ", changes, version=version) is call.return_value
    operation, parameters = call.call_args.args
    assert operation == "update_resource" and parameters[0] == " s "
    assert parameters[2] == version
    payload = parameters[1]
    if changes is None:
        assert payload is None  # SQL NULL, not a JSON null wrapper.
    else:
        assert isinstance(payload, Jsonb)
        assert json.loads(JsonbDumper(Jsonb).dump(payload)) == changes
        assert payload.obj is not changes
        assert changes == original
        changes["name"] = "caller changed later"
        assert payload.obj == original
    call.assert_called_once()


@pytest.mark.parametrize("changes", [
    True, 1, "{}", [], ["name"], {1: "value"}, {"name": True},
    {"description": 1.5}, {"name": []}, {"name": {"secret": "content"}},
    {"name": b"SECRET"}, {"name": object()},
])
def test_s4_020_invalid_changes(call: MagicMock, changes: Any) -> None:
    response = arkkan.update_resource("s", changes)
    assert response == {
        "operation_name": "update_resource", "message_type": "response",
        "result": "error",
        "reason": "Changes must be an object with string keys and string or null values.",
    }
    call.assert_not_called()


@pytest.mark.parametrize("value", [True, 1, 1.5, b"SECRET", [], {}, Jsonb("SECRET")])
def test_s4_021_invalid_text_arguments(call: MagicMock, value: Any) -> None:
    cases = [
        ("add_resource_type", {"slug": "s", "description": None}),
        ("update_resource_type", {"slug": "s", "description": None}),
        ("delete_resource_type", {"slug": "s"}),
        ("add_resource", {"slug": "s", "version": "v", "type_slug": "task",
                          "name": "n", "description": "d", "content": "c",
                          "version_info": "i", "state": "disabled"}),
        ("update_resource", {"slug": "s", "version": "v"}),
    ]
    for name, parameters in cases:
        for field in parameters:
            arguments = {**parameters, field: value}
            if name == "update_resource":
                arguments["changes"] = {"version_info": "info"}
            response = getattr(arkkan, name)(**arguments)
            assert response == {
                "operation_name": name, "message_type": "response", "result": "error",
                "reason": "Text arguments must be strings or null.",
            }
    call.assert_not_called()


@pytest.mark.parametrize("name", _WRITE_NAMES)
@pytest.mark.parametrize("result", ["success", "error"])
def test_s4_022_response_passthrough(call: MagicMock, name: str, result: str) -> None:
    response = {"operation_name": name, "message_type": "response", "result": result}
    response.update({"data": {"slug": "s"}} if result == "success"
                    else {"reason": "Access denied."})
    call.return_value = response
    arguments = {
        "add_resource": ("s", "v"), "update_resource": ("s", {"name": None}),
        "add_resource_type": ("s",), "update_resource_type": ("s", None),
        "delete_resource_type": ("s",),
    }
    assert getattr(arkkan, name)(*arguments[name]) is response
    call.assert_called_once()


@pytest.mark.parametrize("name", _WRITE_NAMES)
@pytest.mark.parametrize("malformation", ["missing", "excess", "unknown", "duplicate"])
def test_s4_023_malformed_call(call: MagicMock, name: str, malformation: str) -> None:
    function = getattr(arkkan, name)
    with pytest.raises(TypeError):
        if malformation == "missing":
            function()
        elif malformation == "excess":
            function(*("value",) * 9)
        elif malformation == "unknown":
            function("s", unknown="value")
        else:
            function("s", slug="duplicate")
    call.assert_not_called()

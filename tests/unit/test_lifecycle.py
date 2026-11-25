"""S4-024–029: lifecycle wrapper contracts without database connections."""

from unittest.mock import MagicMock

import pytest

import arkkan

_CALLS = {
    "delete_resource_version": {"slug": "s", "version": "v"},
    "delete_resource_version_all": {"slug": "s"},
    "clean_up": {},
    "delete_resource": {"slug": "s"},
    "set_resource_state": {"slug": "s", "version": "v", "target_state": "disabled"},
    "set_resource_state_all": {"slug": "s", "target_state": "enabled"},
    "set_resource_state_all_with_guard": {
        "slug": "s", "source_state": "disabled", "target_state": "obsolete",
    },
}


@pytest.fixture
def call(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    execution = MagicMock()
    monkeypatch.setattr("arkkan._write._call", execution)
    return execution


def test_s4_024_complete_exports() -> None:
    expected = set(_CALLS) | {
        "add_resource", "update_resource", "add_resource_type",
        "update_resource_type", "delete_resource_type", "get_resource_content",
        "get_resource_info", "get_resource_version_default", "list_resources_matching_type",
    }
    assert set(arkkan.__all__) == expected
    assert len(arkkan.__all__) == 16
    for name in expected:
        assert callable(getattr(arkkan, name))
        assert getattr(arkkan, name).__doc__


@pytest.mark.parametrize("name", _CALLS)
@pytest.mark.parametrize("keyword", [False, True])
@pytest.mark.parametrize("text", ["original", "", " \u2603 '; -- ", None, "invalid_state"])
def test_s4_025_mapping(
    call: MagicMock, name: str, keyword: bool, text: str | None,
) -> None:
    arguments = _CALLS[name].copy()
    if text != "original":
        arguments = dict.fromkeys(arguments, text)
    expected = tuple(arguments.values())
    if name == "set_resource_state":
        expected += (False,)
    function = getattr(arkkan, name)
    response = function(**arguments) if keyword else function(*arguments.values())
    assert response is call.return_value
    call.assert_called_once_with(name, expected)


@pytest.mark.parametrize("force", [False, True, None])
@pytest.mark.parametrize("keyword", [False, True])
def test_s4_026_force_mapping(call: MagicMock, force: bool | None, keyword: bool) -> None:
    if keyword:
        response = arkkan.set_resource_state("s", "v", "disabled", force=force)
    else:
        response = arkkan.set_resource_state("s", "v", "disabled", force)
    assert response is call.return_value
    call.assert_called_once_with("set_resource_state", ("s", "v", "disabled", force))


@pytest.mark.parametrize("value", [True, 0, 1, 1.5, "true", b"secret", [], {}, object()])
def test_s4_027_invalid_types(call: MagicMock, value: object) -> None:
    for name, parameters in _CALLS.items():
        for field in parameters:
            # Strings are legitimate text inputs, even when SQL will reject a value.
            if isinstance(value, str):
                continue
            response = getattr(arkkan, name)(**{**parameters, field: value})
            assert response == {
                "operation_name": name, "message_type": "response", "result": "error",
                "reason": "Text arguments must be strings or null.",
            }
    if isinstance(value, bool):
        call.assert_not_called()
        return
    response = arkkan.set_resource_state("s", "v", "disabled", force=value)
    assert response == {
        "operation_name": "set_resource_state", "message_type": "response",
        "result": "error", "reason": "Force must be a boolean or null.",
    }
    call.assert_not_called()


@pytest.mark.parametrize("name", _CALLS)
@pytest.mark.parametrize("data", [None, {"changed_count": 0}, {"deleted_count": 0},
                                 {"slug": "s", "version": "v", "state": "enabled"}])
def test_s4_028_response_passthrough(call: MagicMock, name: str, data: dict | None) -> None:
    response = {"operation_name": name, "message_type": "response"}
    response.update({"result": "error", "reason": "Access denied."} if data is None
                    else {"result": "success", "data": data})
    call.return_value = response
    assert getattr(arkkan, name)(**_CALLS[name]) is response
    call.assert_called_once()


@pytest.mark.parametrize("name", _CALLS)
def test_s4_029_malformed_calls(call: MagicMock, name: str) -> None:
    function = getattr(arkkan, name)
    with pytest.raises(TypeError):
        function(*("value",) * 5)
    with pytest.raises(TypeError):
        function(**_CALLS[name], unknown=True)
    if _CALLS[name]:
        with pytest.raises(TypeError):
            function()
        with pytest.raises(TypeError):
            function("s", **_CALLS[name])
    if name in {"set_resource_state_all", "set_resource_state_all_with_guard"}:
        with pytest.raises(TypeError):
            function(**_CALLS[name], force=True)
    call.assert_not_called()

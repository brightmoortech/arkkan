"""CLI lifecycle/deletion boundaries; no PostgreSQL connections."""

import json
from typing import Any
from unittest.mock import Mock

import pytest

import arkkan
from arkkan import _api, _cli


@pytest.fixture(autouse=True)
def _no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args: object, **kwargs: object) -> None:
        pytest.fail("CLI unit test attempted a database connection")

    monkeypatch.setattr(_api.psycopg, "connect", reject)


# Explicit expectations stay independent of the CLI parser/dispatch tables.
CASES = [
    (["type", "delete", "slug"], "delete_resource_type", ("slug",), {},
     {"slug": "slug"}, "Deleted type: slug\n"),
    (["resource", "delete-version", "slug", "-v", "v1"],
     "delete_resource_version", ("slug", "v1"), {},
     {"slug": "slug", "version": "v1"}, "Deleted slug version v1\n"),
    (["resource", "delete-obsolete", "slug"], "delete_resource_version_all",
     ("slug",), {}, {"slug": "slug", "deleted_count": 3},
     "Deleted obsolete versions for slug: 3\n"),
    (["resource", "cleanup"], "clean_up", (), {}, {"deleted_count": 3},
     "Deleted obsolete versions: 3\n"),
    (["resource", "delete", "slug"], "delete_resource", ("slug",), {},
     {"slug": "slug", "deleted_version_count": 3},
     "Deleted resource slug; versions: 3\n"),
    (["resource", "state", "slug", "-v", "v1", "-s", "enabled"],
     "set_resource_state", ("slug", "v1", "enabled"), {"force": False},
     {"slug": "slug", "version": "v1", "state": "enabled"},
     "Updated slug version v1: enabled\n"),
    (["resource", "state-all", "slug", "-s", "enabled"],
     "set_resource_state_all", ("slug", "enabled"), {},
     {"slug": "slug", "changed_count": 3}, "Updated versions for slug: 3\n"),
    (["resource", "state-matching", "slug", "-g", "disabled", "-s", "enabled"],
     "set_resource_state_all_with_guard", ("slug", "disabled", "enabled"), {},
     {"slug": "slug", "changed_count": 3}, "Updated versions for slug: 3\n"),
]


@pytest.mark.parametrize("command,operation,parameters,keywords,data,expected", CASES)
@pytest.mark.parametrize("mode", ["human", "json", "human-error", "json-error"])
def test_s5_019_lifecycle_mapping_and_output(
    command: list[str], operation: str, parameters: tuple[str, ...],
    keywords: dict[str, bool], data: dict[str, Any], expected: str, mode: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    failed = mode.endswith("error")
    response = {"operation_name": operation, "message_type": "response",
                "result": "error" if failed else "success"}
    response.update({"reason": "Permission denied."} if failed else {"data": data})
    doubles = {name: Mock(return_value=response) for name in arkkan.__all__}
    for name, double in doubles.items():
        monkeypatch.setattr(arkkan, name, double)
    json_output = mode.startswith("json")
    assert _cli._main([*command, *(["-j"] if json_output else [])]) == int(failed)
    doubles[operation].assert_called_once_with(*parameters, **keywords)
    assert all(not double.called for name, double in doubles.items() if name != operation)
    captured = capsys.readouterr()
    if json_output:
        assert json.loads(captured.out) == response
        assert captured.err == ""
    elif failed:
        assert captured.out == ""
        assert captured.err == "arkkan: Permission denied.\n"
    else:
        assert captured.out == expected
        assert captured.err == ""


@pytest.mark.parametrize("command,operation,parameters,keywords,data,expected", CASES)
@pytest.mark.parametrize("literal", ["", "  ", " 雪 '; -- "])
def test_s5_020_literal_lifecycle_tokens(
    command: list[str], operation: str, parameters: tuple[str, ...],
    keywords: dict[str, bool], data: dict[str, Any], expected: str, literal: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = [literal if token in parameters else token for token in command]
    response = {"operation_name": operation, "message_type": "response",
                "result": "success", "data": data}
    double = Mock(return_value=response)
    monkeypatch.setattr(arkkan, operation, double)
    assert _cli._main([*arguments, "-j"]) == 0
    double.assert_called_once_with(*(literal for _ in parameters), **keywords)
    assert json.loads(capsys.readouterr().out) == response


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("state", ["enabled", "enabled_default", "disabled", "obsolete", "INVALID"])
def test_s5_021_force_and_state_policy(
    force: bool, state: str, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    response = {"operation_name": "set_resource_state", "message_type": "response",
                "result": "error", "reason": "State transition is not allowed."}
    double = Mock(return_value=response)
    monkeypatch.setattr(arkkan, "set_resource_state", double)
    assert _cli._main(["resource", "state", "slug", "-s", state, "-v", "v1",
                       *(["-F"] if force else []), "-j"]) == 1
    double.assert_called_once_with("slug", "v1", state, force=force)
    assert json.loads(capsys.readouterr().out) == response


@pytest.mark.parametrize("command,operation,parameters,keywords,data,expected", [
    case for case in CASES if any(key.endswith("count") for key in case[4])
])
def test_s5_022_zero_counts(
    command: list[str], operation: str, parameters: tuple[str, ...],
    keywords: dict[str, bool], data: dict[str, Any], expected: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    payload = {key: 0 if key.endswith("count") else value for key, value in data.items()}
    response = {"operation_name": operation, "message_type": "response",
                "result": "success", "data": payload}
    monkeypatch.setattr(arkkan, operation, Mock(return_value=response))
    assert _cli._main(command) == 0
    captured = capsys.readouterr()
    assert captured.out == expected.replace("3", "0")
    assert captured.err == ""


@pytest.mark.parametrize("arguments", [
    ["type", "delete"], ["type", "delete", "task", "-d", "description"],
    ["resource", "delete-version", "slug"],
    ["resource", "delete-version", "slug", "-v"],
    ["resource", "delete-version", "-v", "v1"],
    ["resource", "delete-obsolete"], ["resource", "delete"],
    ["resource", "cleanup", "slug"],
    ["resource", "state", "slug", "-v", "v1"],
    ["resource", "state", "slug", "-s", "enabled"],
    ["resource", "state-all", "slug"],
    ["resource", "state-matching", "slug", "-s", "enabled"],
    ["resource", "state-matching", "slug", "-g", "disabled"],
    ["resource", "state", "slug", "-v", "v1", "-s"],
    *[case[0] + ["--hel"] for case in CASES],
    *[case[0] + ["-F"] for case in CASES if case[1] != "set_resource_state"],
    *[command + ["-F"] for command in (
        ["resource", "get", "slug"], ["resource", "list", "-t", "task"],
        ["resource", "default", "slug"], ["resource", "info", "slug"],
        ["resource", "add", "slug", "v1"],
        ["resource", "update", "slug", "--clear-name"],
        ["type", "add", "task"], ["type", "update", "task", "--clear-description"],
    )],
    ["resource", "state", "slug", "-v", "v1", "-s", "enabled", "-g", "disabled"],
    ["resource", "state-all", "slug", "-s", "enabled", "-v", "v1"],
    ["resource", "state-matching", "slug", "-g", "disabled", "-s", "enabled", "-v", "v1"],
    ["resource", "delete", "slug", "-s", "obsolete"],
])
def test_s5_023_invalid_lifecycle_arguments(
    arguments: list[str], monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    doubles = {name: Mock() for name in arkkan.__all__}
    for name, double in doubles.items():
        monkeypatch.setattr(arkkan, name, double)
    with pytest.raises(SystemExit) as error:
        _cli._main(arguments)
    assert error.value.code == 2
    assert all(not double.called for double in doubles.values())
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error:" in captured.err


@pytest.mark.parametrize("prefix", [case[0][:2] for case in CASES])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_s5_024_lifecycle_help(
    prefix: list[str], flag: str, capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        _cli._main([*prefix, flag])
    assert error.value.code == 0
    captured = capsys.readouterr()
    assert f"usage: arkkan {' '.join(prefix)}" in captured.out
    assert "-j" in captured.out
    assert ("-F" in captured.out) == (prefix == ["resource", "state"])
    assert captured.err == ""

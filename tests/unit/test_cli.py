"""CLI boundary tests; public API doubles and no database connections."""

import json
import os
from pathlib import Path
import subprocess
import sys
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


def _response(operation: str, data: Any) -> dict[str, Any]:
    return {
        "operation_name": operation, "message_type": "response",
        "result": "success", "data": data,
    }


@pytest.mark.parametrize("arguments", [
    [], ["resource"], ["type"], ["setup"], ["resource", "unknown"],
    ["resource", "get"], ["resource", "get", "slug", "extra"],
    ["resource", "get", "slug", "-v"],
    ["resource", "get", "slug", "-m", "strict"],
    ["resource", "get", "slug", "-v", "v1", "-m", "STRICT"],
    ["resource", "get", "slug", "--password", "not-a-secret"],
    ["resource", "get", "slug", "--hel"],
    ["resource", "list"], ["resource", "list", "-t"],
    ["resource", "list", "slug", "-t", "task"],
    ["resource", "default", "slug", "-v", "v1"],
    ["resource", "info", "slug", "-m", "strict"],
    ["-j", "resource", "info", "slug"],
])
def test_s5_001_invalid_arguments(
    arguments: list[str], capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doubles = [Mock() for _ in arkkan.__all__]
    for name, double in zip(arkkan.__all__, doubles):
        monkeypatch.setattr(arkkan, name, double)
    with pytest.raises(SystemExit) as error:
        _cli._main(arguments)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error:" in captured.err
    assert all(not double.called for double in doubles)


@pytest.mark.parametrize("prefix", [
    [], ["resource"], ["type"], ["resource", "get"],
    ["resource", "list"], ["resource", "default"], ["resource", "info"],
])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_s5_002_help(
    prefix: list[str], flag: str, capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        _cli._main([*prefix, flag])
    assert error.value.code == 0
    captured = capsys.readouterr()
    assert "usage: arkkan" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize("arguments,operation,parameters", [
    (["get", " Slug 雪 "], "get_resource_content", (" Slug 雪 ",)),
    (["get", "slug", "-v", "opaque"], "get_resource_content", ("slug", "opaque")),
    *[(["get", "slug", "-v", "v1", "-m", mode],
       "get_resource_content", ("slug", "v1", mode))
      for mode in ("strict", "version_priority", "default_priority")],
    (["get", "", "-v", ""], "get_resource_content", ("", "")),
    (["list", "-t", " Task 雪 "], "list_resources_matching_type", (" Task 雪 ",)),
    (["default", "slug"], "get_resource_version_default", ("slug",)),
    (["info", "quote'; --"], "get_resource_info", ("quote'; --",)),
])
def test_s5_003_read_mapping(
    arguments: list[str], operation: str, parameters: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    response = _response(operation, {"sentinel": "雪", "optional": None})
    double = Mock(return_value=response)
    monkeypatch.setattr(arkkan, operation, double)
    assert _cli._main(["resource", *arguments, "-j"]) == 0
    double.assert_called_once_with(*parameters)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == response
    assert captured.err == ""


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("content", ["", "hello", "雪\n", "line\r\n\n", "  \t"])
def test_s5_004_exact_content(
    content: str, json_output: bool, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(arkkan, "get_resource_content", Mock(return_value=_response(
        "get_resource_content",
        {"slug": "slug", "version": "v1", "state": "enabled", "content": content},
    )))
    arguments = ["resource", "get", "slug", *(["-j"] if json_output else [])]
    assert _cli._main(arguments) == 0
    captured = capsys.readouterr()
    if json_output:
        assert json.loads(captured.out)["data"]["content"] == content
    else:
        assert captured.out == content
    assert captured.err == ""


@pytest.mark.parametrize("command,operation,data,expected", [
    (["list", "-t", "task"], "list_resources_matching_type", [], "No resources found.\n"),
    (["list", "-t", "task"], "list_resources_matching_type",
     [{"slug": "slug", "name": "Name", "description": "Description"},
      {"slug": "empty", "name": None, "description": None}],
     "slug: Name\n  Description: Description\nempty: \n"),
    (["default", "slug"], "get_resource_version_default",
     {"slug": "slug", "version": "v1"}, "slug: v1\n"),
    (["info", "slug"], "get_resource_info",
     {"slug": "slug", "type_slug": "task", "name": None, "description": "", "versions": []},
     "Resource: slug\nType: task\nName: (unset)\nDescription: \nVersions:\n  None\n"),
    (["info", "slug"], "get_resource_info",
     {"slug": "slug", "type_slug": "task", "name": "Name", "description": None,
      "versions": [{"version": "v1", "state": "disabled", "created_at": "2026-11-26T00:00:00Z"}]},
     "Resource: slug\nType: task\nName: Name\nDescription: (unset)\nVersions:\n  v1: disabled (2026-11-26T00:00:00Z)\n"),
])
def test_s5_005_metadata_output(
    command: list[str], operation: str, data: Any, expected: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(arkkan, operation, Mock(return_value=_response(operation, data)))
    assert _cli._main(["resource", *command]) == 0
    captured = capsys.readouterr()
    assert captured.out == expected
    assert captured.err == ""


@pytest.mark.parametrize("command,operation", [
    (["get", "slug"], "get_resource_content"),
    (["list", "-t", "task"], "list_resources_matching_type"),
    (["default", "slug"], "get_resource_version_default"),
    (["info", "slug"], "get_resource_info"),
])
@pytest.mark.parametrize("json_output", [False, True])
def test_s5_006_api_error_output(
    command: list[str], operation: str, json_output: bool,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    response = {"operation_name": operation, "message_type": "response",
                "result": "error", "reason": "Permission denied."}
    monkeypatch.setattr(arkkan, operation, Mock(return_value=response))
    assert _cli._main(["resource", *command, *(["-j"] if json_output else [])]) == 1
    captured = capsys.readouterr()
    if json_output:
        assert json.loads(captured.out) == response
        assert captured.err == ""
    else:
        assert captured.out == ""
        assert captured.err == "arkkan: Permission denied.\n"


def test_s5_007_missing_configuration(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("PGDATABASE", raising=False)
    monkeypatch.delenv("PGUSER", raising=False)
    assert _cli._main(["resource", "get", "slug", "-j"]) == 1
    captured = capsys.readouterr()
    response = json.loads(captured.out)
    assert response["result"] == "error"
    assert "PGDATABASE" in response["reason"]
    assert captured.err == ""


def test_s5_008_installed_entry_point(tmp_path: Path) -> None:
    executable = Path(sys.executable).parent / "arkkan"
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    result = subprocess.run(
        [str(executable), "resource", "get", "--help"],
        cwd=tmp_path, env=environment, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "usage: arkkan resource get" in result.stdout
    assert "-m MODE" in result.stdout
    assert result.stderr == ""

"""CLI creation/update contracts with public API doubles, no database."""

import io
import itertools
import json
from pathlib import Path
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


def _success(operation: str, data: Any) -> dict[str, Any]:
    return {
        "operation_name": operation, "message_type": "response",
        "result": "success", "data": data,
    }


@pytest.mark.parametrize("options,expected", [
    ([], {}),
    (["-t", " Task 雪 ", "-n", "", "-d", " description ", "-i", "info"],
     {"type_slug": " Task 雪 ", "name": "", "description": " description ",
      "version_info": "info"}),
    *[(["-s", state], {"state": state})
      for state in ("enabled", "enabled_default", "obsolete", "unknown", "")],
])
def test_s5_009_add_defaults_and_options(
    options: list[str], expected: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    response = _success("add_resource", {"slug": "literal"})
    double = Mock(return_value=response)
    monkeypatch.setattr(arkkan, "add_resource", double)
    arguments = dict(type_slug=None, name=None, description=None, content="",
                     version_info=None, state="disabled")
    arguments.update(expected)
    assert _cli._main(["resource", "add", " Slug '; 雪 ", " v1 ", *options, "-j"]) == 0
    double.assert_called_once_with(" Slug '; 雪 ", " v1 ", **arguments)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == response
    assert captured.err == ""


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("content", ["", "雪 العربية", "\ufefftext\r\n\n", "  \t\rtext\n"])
def test_s5_010_utf8_content(
    source: str, content: str, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    original = content.encode("utf-8")
    path = tmp_path / "content.txt"
    path.write_bytes(original)
    # A deliberately different text encoding proves the binary stdin path is used.
    stream = io.TextIOWrapper(io.BytesIO(original), encoding="ascii")
    monkeypatch.setattr(_cli.sys, "stdin", stream)
    double = Mock(return_value=_success("add_resource", {"slug": "slug"}))
    monkeypatch.setattr(arkkan, "add_resource", double)
    filename = str(path) if source == "file" else "-"
    assert _cli._main(["resource", "add", "slug", "v1", "-f", filename, "-j"]) == 0
    assert double.call_args.kwargs["content"] == content
    assert path.read_bytes() == original
    assert not stream.closed
    assert capsys.readouterr().err == ""
    stream.close()


@pytest.mark.parametrize("source", ["file", "stdin", "missing", "directory", "null-path"])
@pytest.mark.parametrize("json_output", [False, True])
def test_s5_011_content_errors_before_api(
    source: str, json_output: bool, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "content.txt"
    original = b"sensitive-content\xff"
    path.write_bytes(original)
    stream = io.TextIOWrapper(io.BytesIO(original), encoding="utf-8", errors="replace")
    monkeypatch.setattr(_cli.sys, "stdin", stream)
    filename = {"file": str(path), "stdin": "-", "missing": str(tmp_path / "missing"),
                "directory": str(tmp_path), "null-path": "bad\0path"}[source]
    double = Mock()
    monkeypatch.setattr(arkkan, "add_resource", double)
    with pytest.raises(SystemExit) as error:
        _cli._main(["resource", "add", "slug", "v1", "-f", filename,
                    *(["-j"] if json_output else [])])
    assert error.value.code == 2
    double.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error:" in captured.err
    assert "sensitive-content" not in captured.err
    assert "Traceback" not in captured.err
    assert path.read_bytes() == original
    assert not stream.closed
    stream.close()


@pytest.mark.parametrize("states", list(itertools.product(
    ("omitted", "set", "empty", "clear"), repeat=3,
))[1:])
def test_s5_012_metadata_changes(
    states: tuple[str, str, str], monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fields = (("name", "-n", "--clear-name"),
              ("description", "-d", "--clear-description"),
              ("version_info", "-i", "--clear-info"))
    options: list[str] = []
    changes: dict[str, str | None] = {}
    for (field, setter, clearer), state in zip(fields, states):
        if state == "omitted":
            continue
        value = None if state == "clear" else "" if state == "empty" else "literal 雪"
        changes[field] = value
        options.extend([clearer] if state == "clear" else [setter, value])
    version = " v1 " if "version_info" in changes else None
    if version is not None:
        options.extend(["-v", version])
    response = _success("update_resource", {"slug": "slug", "updated_fields": list(changes)})
    double = Mock(return_value=response)
    monkeypatch.setattr(arkkan, "update_resource", double)
    assert _cli._main(["resource", "update", "slug", *options, "-j"]) == 0
    double.assert_called_once_with("slug", changes, version=version)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == response
    assert captured.err == ""


@pytest.mark.parametrize("command,operation,description", [
    (["add", " type 雪 "], "add_resource_type", None),
    (["add", " type 雪 ", "-d", ""], "add_resource_type", ""),
    (["add", " type 雪 ", "-d", "Description"], "add_resource_type", "Description"),
    (["update", " type 雪 ", "--clear-description"], "update_resource_type", None),
    (["update", " type 雪 ", "-d", ""], "update_resource_type", ""),
    (["update", " type 雪 ", "-d", "Description"], "update_resource_type", "Description"),
])
def test_s5_013_type_mapping(
    command: list[str], operation: str, description: str | None,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    response = _success(operation, {"slug": " type 雪 "})
    double = Mock(return_value=response)
    monkeypatch.setattr(arkkan, operation, double)
    assert _cli._main(["type", *command, "-j"]) == 0
    double.assert_called_once_with(" type 雪 ", description)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == response
    assert captured.err == ""


@pytest.mark.parametrize("arguments", [
    ["resource", "add"], ["resource", "add", "slug"],
    ["resource", "add", "slug", "v1", "-t"],
    ["resource", "add", "slug", "v1", "--clear-name"],
    ["resource", "update", "slug"],
    ["resource", "update", "slug", "-v", "v1"],
    ["resource", "update", "slug", "-n", "Name", "-v", "v1"],
    ["resource", "update", "slug", "-i", ""],
    ["resource", "update", "slug", "--clear-info"],
    *[["resource", "update", "slug", flag, "value", clear]
      for flag, clear in (("-n", "--clear-name"), ("-d", "--clear-description"),
                          ("-i", "--clear-info"))],
    ["resource", "update", "slug", "--clear-desc"],
    ["resource", "update", "slug", "-f", "-"],
    ["type", "add"], ["type", "add", "task", "--clear-description"],
    ["type", "update", "task"],
    ["type", "update", "task", "-d", "", "--clear-description"],
    ["type", "update", "task", "-i", "info"],
    ["type", "update", "task", "--clear-desc"],
])
def test_s5_014_invalid_write_arguments(
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


@pytest.mark.parametrize("group,command", [
    ("resource", "add"), ("resource", "update"),
    ("type", "add"), ("type", "update"),
])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_s5_015_write_help(
    group: str, command: str, flag: str, capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        _cli._main([group, command, flag])
    assert error.value.code == 0
    captured = capsys.readouterr()
    assert f"usage: arkkan {group} {command}" in captured.out
    assert "-j" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize("command,operation,data,expected", [
    (["resource", "add", "slug", "v1"], "add_resource",
     {"slug": "slug", "version": "v1", "state": "disabled"},
     "Created slug version v1: disabled\n"),
    (["resource", "update", "slug", "--clear-name"], "update_resource",
     {"slug": "slug", "updated_fields": ["name"]}, "Updated slug: name\n"),
    (["resource", "update", "slug", "-v", "v1", "--clear-info"], "update_resource",
     {"slug": "slug", "version": "v1", "updated_fields": ["version_info"]},
     "Updated slug version v1: version_info\n"),
    (["type", "add", "task"], "add_resource_type", {"slug": "task"},
     "Created type: task\n"),
    (["type", "update", "task", "--clear-description"], "update_resource_type",
     {"slug": "task", "description": None}, "Updated type description: task\n"),
])
@pytest.mark.parametrize("result", ["human", "json", "human-error", "json-error"])
def test_s5_016_write_output(
    command: list[str], operation: str, data: Any, expected: str, result: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    response = _success(operation, data)
    failed = result.endswith("error")
    if failed:
        response.pop("data")
        response.update(result="error", reason="Permission denied.")
    monkeypatch.setattr(arkkan, operation, Mock(return_value=response))
    json_output = result.startswith("json")
    assert _cli._main([*command, *(["-j"] if json_output else [])]) == int(failed)
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


@pytest.mark.parametrize("source", ["file", "stdin"])
def test_s5_017_read_failure_sanitized(
    source: str, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = Mock(side_effect=PermissionError("private diagnostic and content"))
    if source == "file":
        monkeypatch.setattr(Path, "read_bytes", failure)
    else:
        monkeypatch.setattr(_cli.sys, "stdin", Mock(buffer=Mock(read=failure)))
    double = Mock()
    monkeypatch.setattr(arkkan, "add_resource", double)
    filename = "input.txt" if source == "file" else "-"
    with pytest.raises(SystemExit) as error:
        _cli._main(["resource", "add", "slug", "v1", "-f", filename, "-j"])
    assert error.value.code == 2
    failure.assert_called_once()
    double.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Cannot read content" in captured.err
    assert "private diagnostic" not in captured.err


def test_s5_018_syntax_before_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    stream = Mock(buffer=Mock(read=Mock()))
    monkeypatch.setattr(_cli.sys, "stdin", stream)
    double = Mock()
    monkeypatch.setattr(arkkan, "add_resource", double)
    with pytest.raises(SystemExit) as error:
        _cli._main(["resource", "add", "slug", "v1", "-f", "-", "-F"])
    assert error.value.code == 2
    stream.buffer.read.assert_not_called()
    double.assert_not_called()
    assert capsys.readouterr().out == ""

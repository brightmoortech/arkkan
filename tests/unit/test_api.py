"""S4-001–009: Python execution boundary, without database connections."""

from typing import Any
from unittest.mock import MagicMock

import psycopg
import pytest

from arkkan._api import _call

_Database = tuple[MagicMock, MagicMock, MagicMock]


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch) -> _Database:
    monkeypatch.setenv("PGDATABASE", "test_db")
    monkeypatch.setenv("PGUSER", "arkkan_admin")
    for name in ("PGHOST", "PGPORT", "PGPASSFILE"):
        monkeypatch.delenv(name, raising=False)
    connect = MagicMock()
    connection = connect.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ({
        "operation_name": "add_resource_type", "message_type": "response",
        "result": "success", "data": {"slug": "example", "type_id": "id"},
    },)
    monkeypatch.setattr("arkkan._api.psycopg.connect", connect)
    return connect, connection, cursor


@pytest.mark.parametrize(
    "parameters", [(), (" exact ' ; -- \u2603 ",), (None, "", False)],
)
def test_s4_001_parameterized_call(
    database: _Database, parameters: tuple[Any, ...],
) -> None:
    connect, connection, cursor = database
    result = _call("add_resource_type", parameters)
    query, values = cursor.execute.call_args.args
    placeholders = ", ".join("%s" for _ in parameters)
    expected = f'SELECT "arkkan_api"."add_resource_type"({placeholders})'
    assert query.as_string() == expected
    assert values is parameters
    assert result == cursor.fetchone.return_value[0]
    connect.assert_called_once_with(
        dbname="test_db", user="arkkan_admin", autocommit=False,
    )
    connection.commit.assert_called_once_with()
    connection.rollback.assert_not_called()
    connection.close.assert_called_once_with()
    connection.cursor.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "payload", [{"content": "", "description": None}, [], {"count": 0}],
)
def test_s4_002_decoded_payload(database: _Database, payload: Any) -> None:
    _, _, cursor = database
    cursor.fetchone.return_value[0]["data"] = payload
    assert _call("add_resource_type")["data"] is payload


def test_s4_003_sql_rejection_rolls_back(database: _Database) -> None:
    _, connection, cursor = database
    response = {
        "operation_name": "add_resource_type", "message_type": "response",
        "result": "error", "reason": "Resource type already exists.",
    }
    cursor.fetchone.return_value = (response,)
    assert _call("add_resource_type") == response
    connection.rollback.assert_called_once_with()
    connection.commit.assert_not_called()
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("variable", ["PGDATABASE", "PGUSER"])
def test_s4_004_configuration_failure(
    database: _Database, monkeypatch: pytest.MonkeyPatch, variable: str,
) -> None:
    monkeypatch.setenv(variable, " ")
    assert _call("add_resource_type")["result"] == "error"
    database[0].assert_not_called()


@pytest.mark.parametrize("error_class", [
    psycopg.errors.InsufficientPrivilege,
    psycopg.OperationalError,
    psycopg.ProgrammingError,
])
@pytest.mark.parametrize("step", ["connect", "execute", "fetch", "commit", "rollback"])
def test_s4_005_safe_failures(
    database: _Database, error_class: type[psycopg.Error], step: str,
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture,
) -> None:
    connect, connection, cursor = database
    target = {
        "connect": connect, "execute": cursor.execute, "fetch": cursor.fetchone,
        "commit": connection.commit, "rollback": connection.rollback,
    }[step]
    target.side_effect = error_class("SECRET SQL and prompt content")
    if step == "rollback":
        cursor.execute.side_effect = psycopg.ProgrammingError("SENSITIVE INPUT")
    result = _call("add_resource_type", ("private content",))
    assert set(result) == {"operation_name", "message_type", "result", "reason"}
    assert result["operation_name"] == "add_resource_type"
    assert result["message_type"] == "response"
    assert result["result"] == "error"
    assert result["reason"]
    assert "SECRET" not in str(result) and "SENSITIVE" not in str(result)
    assert "private content" not in str(result)
    assert not caplog.text
    assert capsys.readouterr() == ("", "")
    connect.assert_called_once()
    if step != "connect":
        connection.close.assert_called_once_with()
        connection.rollback.assert_called_once_with()
    if step == "commit":
        assert "outcome before retrying" in result["reason"]
    elif error_class is psycopg.errors.InsufficientPrivilege:
        assert "Access denied" in result["reason"]
    elif error_class is psycopg.OperationalError:
        assert "connection settings" in result["reason"]
    if step != "commit":
        connection.commit.assert_not_called()


@pytest.mark.parametrize("row", [
    None, (), (None,), ("{}",), ({},),
    ({"operation_name": "wrong", "message_type": "response",
      "result": "success", "data": {}},),
    ({"operation_name": "add_resource_type", "message_type": "wrong",
      "result": "success", "data": {}},),
    ({"operation_name": "add_resource_type", "message_type": "response",
      "result": "success"},),
    ({"operation_name": "add_resource_type", "message_type": "response",
      "result": "error", "reason": " "},),
    ({"operation_name": "add_resource_type", "message_type": "response",
      "result": "error", "reason": 1},),
])
def test_s4_006_invalid_response(database: _Database, row: Any) -> None:
    _, connection, cursor = database
    cursor.fetchone.return_value = row
    result = _call("add_resource_type")
    assert result["result"] == "error" and "API response" in result["reason"]
    connection.rollback.assert_called_once_with()
    connection.commit.assert_not_called()
    connection.close.assert_called_once_with()


@pytest.mark.parametrize("exception", [KeyboardInterrupt, RuntimeError])
def test_s4_007_unexpected_failure_closes(
    database: _Database, exception: type[BaseException],
) -> None:
    _, connection, cursor = database
    cursor.execute.side_effect = exception()
    with pytest.raises(exception):
        _call("add_resource_type")
    connection.commit.assert_not_called()
    connection.close.assert_called_once_with()


def test_s4_008_configuration_per_call(
    database: _Database, monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect, _, _ = database
    _call("add_resource_type")
    monkeypatch.setenv("PGUSER", "arkkan_user")
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGPORT", "5442")
    monkeypatch.setenv("PGPASSFILE", "/external/client-password-file")
    _call("add_resource_type")
    assert connect.call_count == 2
    connect.assert_called_with(
        dbname="test_db", user="arkkan_user", host="localhost",
        port="5442", passfile="/external/client-password-file", autocommit=False,
    )


@pytest.mark.parametrize("commit_failure", [False, True])
def test_s4_009_rollback_failure_closes(
    database: _Database, commit_failure: bool, caplog: pytest.LogCaptureFixture,
) -> None:
    _, connection, cursor = database
    if commit_failure:
        connection.commit.side_effect = psycopg.OperationalError("SECRET commit")
    else:
        cursor.fetchone.return_value = ({
            "operation_name": "add_resource_type", "message_type": "response",
            "result": "error", "reason": "Resource type already exists.",
        },)
    connection.rollback.side_effect = psycopg.OperationalError("SECRET rollback")
    result = _call("add_resource_type")
    assert result["result"] == "error"
    assert "SECRET" not in str(result) and not caplog.text
    if commit_failure:
        assert "outcome before retrying" in result["reason"]
    connection.rollback.assert_called_once_with()
    connection.close.assert_called_once_with()

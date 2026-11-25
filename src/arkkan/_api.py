"""Internal execution boundary for the public Python resource wrappers."""

from contextlib import closing
from typing import Any

import psycopg
from psycopg import sql

from arkkan._config import _connection_settings


class _InvalidResponse(ValueError):
    """The installed SQL API returned an incompatible response envelope."""


def _error_response(operation_name: str, reason: str) -> dict[str, Any]:
    return {
        "operation_name": operation_name,
        "message_type": "response",
        "result": "error",
        "reason": reason,
    }


def _response(operation_name: str, row: tuple[Any, ...] | None) -> dict[str, Any]:
    """Check the common envelope without reinterpreting operation payloads."""
    if row is None or len(row) != 1 or not isinstance(row[0], dict):
        raise _InvalidResponse
    response = row[0]
    common = {"operation_name", "message_type", "result"}
    if (
        response.get("operation_name") != operation_name
        or response.get("message_type") != "response"
    ):
        raise _InvalidResponse
    if response.get("result") == "success" and set(response) == common | {"data"}:
        return response
    if (
        response.get("result") == "error"
        and set(response) == common | {"reason"}
        and isinstance(response["reason"], str)
        and response["reason"].strip()
    ):
        return response
    raise _InvalidResponse


def _call(operation_name: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any]:
    """Call a wrapper-selected SQL function in one owned transaction.

    Wrappers supply the fixed operation name and already adapted parameters.
    Psycopg decodes JSONB. SQL owns validation and lifecycle policies. Calls
    never retry: a lost commit acknowledgement can leave the outcome unknown.
    """
    try:
        configuration = _connection_settings()
    except ValueError:
        return _error_response(
            operation_name, "Set nonblank PGDATABASE and PGUSER before calling the API."
        )

    option_names = {
        "PGDATABASE": "dbname", "PGUSER": "user", "PGHOST": "host",
        "PGPORT": "port", "PGPASSFILE": "passfile",
    }
    settings = {option_names[name]: value for name, value in configuration.items()}
    query = sql.SQL("SELECT {}({})").format(
        sql.Identifier("arkkan_api", operation_name),
        sql.SQL(", ").join(sql.Placeholder() for _ in parameters),
    )
    committing = False
    try:
        # Own cleanup explicitly: Connection.__exit__ can skip closing after a
        # commit failure and log raw diagnostics after a rollback failure.
        with closing(psycopg.connect(**settings, autocommit=False)) as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query, parameters)
                    response = _response(operation_name, cursor.fetchone())
                if response["result"] == "success":
                    committing = True
                    connection.commit()
            except (psycopg.Error, _InvalidResponse):
                connection.rollback()
                raise
            if response["result"] == "error":
                connection.rollback()
            return response
    except _InvalidResponse:
        reason = "Invalid database API response. Verify the installed API migrations."
    except psycopg.Error as error:
        if committing:
            reason = "Commit failed. Verify the operation's outcome before retrying."
        elif isinstance(error, psycopg.errors.InsufficientPrivilege):
            reason = "Access denied. Use a database role authorized for this operation."
        elif isinstance(error, psycopg.OperationalError):
            reason = (
                "Database connection or operation failed. Check connection settings, "
                "credentials and server availability."
            )
        else:
            reason = (
                "Database operation failed. Check inputs and installed API migrations."
            )
    return _error_response(operation_name, reason)

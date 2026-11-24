"""Project-independent, ordered PostgreSQL migration orchestration."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg import Connection


@dataclass(frozen=True)
class _Migration:
    """A named step: inspect without writes, apply missing work, verify state."""

    name: str
    check: Callable[["Connection[Any]"], bool]
    apply: Callable[["Connection[Any]"], None]
    verify: Callable[["Connection[Any]"], None] | None = None


def _inspect(connection: "Connection[Any]", migration: _Migration) -> bool:
    try:
        return migration.check(connection)
    except ValueError as error:
        raise ValueError(f"{migration.name}: {error}") from None


def _plan(
    connection: "Connection[Any]", migrations: Sequence[_Migration],
) -> list[bool]:
    # Inspect every step before any write. Missing prerequisites are pending;
    # conflicting objects are errors, including conflicts in later steps.
    with connection.transaction():
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL search_path = pg_catalog")
        return [_inspect(connection, migration) for migration in migrations]


def _run_migrations(
    connection: "Connection[Any]", migrations: Sequence[_Migration], *,
    apply: bool, lock_key: int, report: Callable[[str], None] = print,
) -> None:
    """Plan read-only or apply in order, committing only verified steps.

    The connection must be idle and autocommit enabled. Check callbacks return
    True for compliant state, False for missing work, or raise ValueError for
    conflicts. Callbacks must not commit or manage their own transactions.
    """
    if not connection.autocommit or connection.info.transaction_status != 0:
        raise ValueError("Initialization requires an idle autocommit connection.")
    names = [migration.name for migration in migrations]
    if not names or len(set(names)) != len(names):
        raise ValueError("The ordered migration list is empty or contains duplicate names.")
    # A session lock serializes cooperating apply runs across step commits.
    # Check mode does not acquire a lock or perform any persistent writes.
    locked = False
    committed = 0
    try:
        if apply:
            locked = bool(connection.execute(
                "SELECT pg_catalog.pg_try_advisory_lock(%s::bigint)", (lock_key,)
            ).fetchone()[0])
            if not locked:
                raise ValueError("Another initialization is running; retry after it completes.")
        statuses = _plan(connection, migrations)
        for migration, ready in zip(migrations, statuses, strict=True):
            report(f"[{'UNCHANGED' if ready else 'PENDING'}] {migration.name}")
        if not apply:
            report("[OK] Dry run complete. No database changes made.")
            return
        for migration in migrations:
            completed = False
            changed = False
            try:
                with connection.transaction():
                    connection.execute("SET LOCAL search_path = pg_catalog")
                    # Recheck under the actual step transaction.
                    if not _inspect(connection, migration):
                        migration.apply(connection)
                        if not _inspect(connection, migration):
                            raise ValueError("Expected objects are still missing after apply.")
                        if migration.verify is not None:
                            migration.verify(connection)
                        changed = True
                completed = True
            finally:
                if not completed:
                    # A transaction failure rolls back the step. If connection
                    # loss obscured a commit result, do not claim its outcome.
                    report(f"[STOPPED] {migration.name}; {committed} earlier "
                           "applied step(s) confirmed committed. Verify before retrying.")
            if changed:
                committed += 1
                report(f"[APPLIED] {migration.name}")
        if not all(_plan(connection, migrations)):
            raise ValueError("Final verification found missing objects; earlier commits remain.")
        report(f"[OK] Initialization steps complete. {committed} step(s) applied.")
    finally:
        if locked and not connection.closed and not connection.broken:
            connection.execute(
                "SELECT pg_catalog.pg_advisory_unlock(%s::bigint)", (lock_key,)
            )

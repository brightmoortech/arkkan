"""Require staging verification at entry to database test suites."""

from pathlib import Path

import pytest

from arkkan._test_safety import _staging_connection


@pytest.fixture(autouse=True)
def _database_suite_guard(request: pytest.FixtureRequest) -> None:
    tests_root = Path(__file__).resolve().parent
    test_path = request.path.resolve()
    if any(test_path.is_relative_to(tests_root / suite) for suite in ("integration", "e2e")):
        try:
            with _staging_connection(tests_root.parent):
                pass
        except ValueError as error:
            pytest.fail(f"Staging safety verification failed: {error}", pytrace=False)
        except (OSError, ImportError):
            pytest.fail(
                "Staging safety verification failed: configuration, storage "
                "or the PostgreSQL driver is unavailable.", pytrace=False,
            )

"""Package foundation tests."""


def test_s1_001_package_import() -> None:
    import arkkan

    assert arkkan.__name__ == "arkkan"

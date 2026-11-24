"""Exercise provisioning and test safety without contacting Docker or PostgreSQL."""

import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from arkkan import _provisioning as provision
from arkkan import _test_safety as safety


@pytest.fixture
def settings(tmp_path: Path) -> dict[str, str]:
    settings = {
        "ARKKAN_ENVIRONMENT": "staging",
        "COMPOSE_PROJECT_NAME": "sample_stage",
        "POSTGRES_CONTAINER_NAME": "sample-db-test",
        "PGHOST": "localhost", "PGPORT": "5434", "PGDATABASE": "sample_test",
        "PGUSER": "sample_owner", "PGPASSFILE": str(tmp_path / "pgpass"),
        "POSTGRES_DATA_DIR": str(tmp_path / "data"),
        "POSTGRES_PASSWORD_FILE": str(tmp_path / "password"),
    }
    for key, content in (
        ("PGPASSFILE",
         b"localhost:5434:sample_test:sample_owner:synthetic\n"),
        ("POSTGRES_PASSWORD_FILE", b"synthetic\n"),
    ):
        file = Path(settings[key])
        file.write_bytes(content)
        file.chmod(0o600)
    return settings


def _container(settings: dict[str, str]) -> dict[str, Any]:
    return {
        "Id": "abc123", "Name": "/" + settings["POSTGRES_CONTAINER_NAME"],
        "Config": {
            "Image": provision._IMAGE,
            "Healthcheck": {"Test": provision._HEALTH_TEST.copy()},
            "Labels": {
                "com.docker.compose.project": settings["COMPOSE_PROJECT_NAME"],
                "com.docker.compose.service": "postgres",
            },
            "Env": [
                "POSTGRES_DB=" + settings["PGDATABASE"],
                "POSTGRES_USER=" + settings["PGUSER"],
                "POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password",
                "POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256",
                "PGDATA=/var/lib/postgresql/18/docker",
            ],
        },
        "HostConfig": {"PortBindings": {"5432/tcp": [
            {"HostIp": "127.0.0.1", "HostPort": settings["PGPORT"]},
        ]}},
        "Mounts": [
            {"Type": "bind", "Source": settings["POSTGRES_DATA_DIR"],
             "Destination": provision._DATA_TARGET, "RW": True},
            {"Type": "bind", "Source": settings["POSTGRES_PASSWORD_FILE"],
             "Destination": provision._PASSWORD_TARGET, "RW": False},
        ],
        "State": {"Running": True, "Health": {"Status": "healthy"}},
        "NetworkSettings": {
            "Ports": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": settings["PGPORT"]}]},
            "Networks": {"sample_default": {"IPAddress": "172.18.0.2"}},
        },
    }


@pytest.mark.parametrize("conflict", [
    "image", "project", "port", "data", "password", "database", "role",
    "extra_mount", "password_env", "healthcheck",
])
def test_s2_012_reject_conflicting_container(
    settings: dict[str, str], conflict: str,
) -> None:
    container = _container(settings)
    provision._container_matches(container, settings)
    if conflict == "image":
        container["Config"]["Image"] = "postgres:other"
    elif conflict == "project":
        container["Config"]["Labels"]["com.docker.compose.project"] = "other"
    elif conflict == "port":
        container["HostConfig"]["PortBindings"]["5432/tcp"][0]["HostPort"] = "9999"
    elif conflict in ("data", "password"):
        container["Mounts"][int(conflict == "password")]["Source"] += "-other"
    elif conflict in ("database", "role"):
        container["Config"]["Env"][int(conflict == "role")] += "-other"
    elif conflict == "extra_mount":
        container["Mounts"].append({"Type": "volume"})
    elif conflict == "healthcheck":
        container["Config"]["Healthcheck"]["Test"] = ["CMD", "pg_isready"]
    else:
        container["Config"]["Env"].append("POSTGRES_PASSWORD=synthetic-secret")
    with pytest.raises(ValueError, match="conflicts") as error:
        provision._container_matches(container, settings)
    assert "synthetic-secret" not in str(error.value)


@pytest.mark.parametrize("overlap", ["same", "parent", "child", "project"])
def test_s2_013_reject_unrelated_infrastructure(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    overlap: str,
) -> None:
    other = _container(settings)
    other["Name"] = "/other"
    if overlap != "project":
        other["Config"]["Labels"]["com.docker.compose.project"] = "other"
        path = Path(settings["POSTGRES_DATA_DIR"])
        other["Mounts"][0]["Source"] = str({
            "same": path, "parent": path.parent, "child": path / "child",
        }[overlap])
    monkeypatch.setattr(provision, "_containers", lambda *_: [other])
    with pytest.raises(ValueError, match="overlaps|unexpected"):
        provision._target(settings, tmp_path)


def test_s2_014_independent_targets(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = dict(settings, POSTGRES_CONTAINER_NAME="other", COMPOSE_PROJECT_NAME="other",
                 POSTGRES_DATA_DIR=str(tmp_path / "other"), PGPORT="5433")
    target = _container(settings)
    monkeypatch.setattr(provision, "_containers", lambda *_: [_container(other), target])
    assert provision._target(settings, tmp_path) == target


@pytest.mark.parametrize("state", [None, "stopped", "unhealthy", "starting", "wrong_mapping"])
def test_s2_015_readiness_failure(settings: dict[str, str], state: str | None) -> None:
    container = _container(settings) if state is not None else None
    if container is not None:
        container["State"] = {"Running": state != "stopped", "Health": {"Status": state}}
        if state == "wrong_mapping":
            container["State"]["Health"]["Status"] = "healthy"
            container["NetworkSettings"]["Ports"] = {}

    with pytest.raises(ValueError, match="not running|not healthy|port mapping"):
        provision._require_ready(container)


@pytest.fixture
def dependencies(monkeypatch: pytest.MonkeyPatch, settings: dict[str, str]) -> dict[str, Any]:
    connection = MagicMock()
    calls = {name: MagicMock() for name in (
        "_require_client_environment", "import_module",
        "_require_local_docker", "_target",
        "_require_port_available", "_compose_up", "_verify_database",
        "_create_identity", "_verify_identity",
    )}
    for name, mock in calls.items():
        monkeypatch.setattr(provision, name, mock)
    calls["_target"].return_value = _container(settings)

    @contextmanager
    def connect(*_: Any) -> Iterator[Any]:
        yield connection

    monkeypatch.setattr(provision, "_connect", connect)
    return {**calls, "connection": connection}


def test_s2_016_check_read_only(tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any]) -> None:
    provision._manage("check", settings, tmp_path)
    dependencies["_compose_up"].assert_not_called()
    dependencies["_create_identity"].assert_not_called()
    dependencies["_require_port_available"].assert_not_called()
    dependencies["_verify_identity"].assert_called_once_with(dependencies["connection"], "staging")
    dependencies["connection"].execute.assert_called_once_with("SET TRANSACTION READ ONLY")
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()


@pytest.mark.parametrize("existing_directory", [False, True])
def test_s2_017_first_provisioning(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
    existing_directory: bool,
) -> None:
    storage = tmp_path / "external" / "postgres"
    settings["POSTGRES_DATA_DIR"] = str(storage)
    if existing_directory:
        storage.mkdir(parents=True)
    previous_inode = storage.stat().st_ino if existing_directory else None
    dependencies["_target"].side_effect = [None, _container(settings)]
    provision._manage("setup", settings, tmp_path)
    assert storage.is_dir() and storage.parent.is_dir()
    if previous_inode is not None:
        assert storage.stat().st_ino == previous_inode
    dependencies["_compose_up"].assert_called_once()
    dependencies["_create_identity"].assert_called_once_with(
        dependencies["connection"], "staging"
    )
    dependencies["_require_port_available"].assert_called_once()


@pytest.mark.parametrize("container_exists", [True, False])
def test_s2_018_existing_storage_never_relabels(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any], container_exists: bool,
) -> None:
    storage = Path(settings["POSTGRES_DATA_DIR"]) / "18" / "docker"
    storage.mkdir(parents=True)
    (storage / "PG_VERSION").write_text("18\n")
    if not container_exists:
        dependencies["_target"].side_effect = [None, _container(settings)]
    dependencies["_verify_identity"].side_effect = ValueError("identity missing")
    with pytest.raises(ValueError, match="identity missing"):
        provision._manage("setup", settings, tmp_path)
    dependencies["_create_identity"].assert_not_called()
    assert (storage / "PG_VERSION").read_text() == "18\n"


def test_s2_019_reject_unknown_storage(tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any]) -> None:
    storage = Path(settings["POSTGRES_DATA_DIR"])
    storage.mkdir()
    (storage / "unrelated").write_text("preserve")
    dependencies["_target"].return_value = None
    with pytest.raises(ValueError, match="Nonempty storage"):
        provision._manage("setup", settings, tmp_path)
    dependencies["_compose_up"].assert_not_called()
    assert (storage / "unrelated").read_text() == "preserve"


@pytest.mark.parametrize("rows", [[], [(False, "staging")], [(True, "invalid")], [(True, "staging"), (True, "staging")]])
def test_s2_020_invalid_identity_rows(rows: list[tuple[bool, str]]) -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = ("r", True, True, True, True, True, True)
    connection.execute.return_value.fetchall.return_value = rows
    with pytest.raises(ValueError, match="missing or invalid"):
        provision._read_identity(connection)


@pytest.mark.parametrize("relation", [None, ("v", True, True, True, True, True, True), ("r", True, True, True, True, False, True)])
def test_s2_021_invalid_identity_structure(relation: tuple[Any, ...] | None) -> None:
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = relation
    with pytest.raises(ValueError, match="missing or invalid"):
        provision._read_identity(connection)


@pytest.mark.parametrize("identity", ["development", "production"])
def test_s2_022_identity_mismatch(monkeypatch: pytest.MonkeyPatch, identity: str) -> None:
    monkeypatch.setattr(provision, "_read_identity", lambda _: identity)
    with pytest.raises(ValueError, match="does not match"):
        provision._verify_identity(MagicMock(), "staging")


@pytest.mark.parametrize("change", ["database", "role", "port", "version", "privilege", "address"])
def test_s2_023_connected_target_verification(settings: dict[str, str], change: str) -> None:
    connection = MagicMock()
    values = [settings["PGDATABASE"], settings["PGUSER"], 5432, provision._SERVER_VERSION, True, "172.18.0.2"]
    connection.execute.return_value.fetchone.return_value = tuple(values)
    provision._verify_database(connection, settings, _container(settings))
    index = ["database", "role", "port", "version", "privilege", "address"].index(change)
    values[index] = "wrong" if index < 2 else 0
    connection.execute.return_value.fetchone.return_value = tuple(values)
    with pytest.raises(ValueError, match="do not match"):
        provision._verify_database(connection, settings, _container(settings))


@pytest.mark.parametrize("failure", ["development", "production", "wrong_host", "wrong_port", "wrong_database", "container", "identity", "unreadable", "connected_target"])
def test_s2_024_guard_fails_closed(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    config = dict(settings)
    if failure in ("development", "production"):
        config["ARKKAN_ENVIRONMENT"] = failure
    requested = dict(config)
    if failure.startswith("wrong_"):
        key = {"wrong_host": "PGHOST", "wrong_port": "PGPORT", "wrong_database": "PGDATABASE"}[failure]
        requested[key] = "wrong"
    connection = MagicMock()

    @contextmanager
    def connect(*_: Any) -> Iterator[Any]:
        if failure == "unreadable":
            raise ValueError("connection failed")
        yield connection

    monkeypatch.setattr(safety, "_load_settings", lambda _: config)
    monkeypatch.setattr(safety, "_require_local_docker", MagicMock())
    monkeypatch.setattr(safety, "_target", MagicMock(return_value=None if failure == "container" else _container(config)))
    monkeypatch.setattr(safety, "_connect", connect)
    monkeypatch.setattr(safety, "_verify_database", MagicMock(side_effect=ValueError("wrong target") if failure == "connected_target" else None))
    monkeypatch.setattr(safety, "_verify_identity", MagicMock(side_effect=ValueError("invalid identity") if failure == "identity" else None))
    with pytest.raises(ValueError):
        with safety._staging_connection(tmp_path, requested):
            pytest.fail("Safety guard yielded an unsafe database connection")


def test_s2_025_guard_accepts_verified_staging(tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    connection = MagicMock()

    @contextmanager
    def connect(*_: Any) -> Iterator[Any]:
        yield connection

    monkeypatch.setattr(safety, "_load_settings", lambda _: settings)
    monkeypatch.setattr(safety, "_require_local_docker", MagicMock())
    monkeypatch.setattr(safety, "_target", MagicMock(return_value=_container(settings)))
    monkeypatch.setattr(safety, "_connect", connect)
    verify = MagicMock()
    monkeypatch.setattr(safety, "_verify_database", MagicMock())
    monkeypatch.setattr(safety, "_verify_identity", verify)
    with safety._staging_connection(tmp_path, settings) as actual:
        assert actual is connection
        verify.assert_called_once_with(connection, "staging")
    connection.execute.assert_called_once_with("SET TRANSACTION READ ONLY")


def test_s2_026_reject_implicit_connection_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PGPASSWORD", "synthetic-secret")
    with pytest.raises(ValueError, match="additional PG") as error:
        provision._require_client_environment()
    assert "synthetic-secret" not in str(error.value)


def test_s2_031_reject_nonlocal_docker(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    docker = MagicMock(side_effect=[
        "remote\n", '[{"Endpoints":{"docker":{"Host":"tcp://remote:2376"}}}]',
    ])
    monkeypatch.setattr(provision, "_docker", docker)
    with pytest.raises(ValueError, match="local Unix-socket"):
        provision._require_local_docker(settings, tmp_path)


def test_s2_032_compose_preserves_infrastructure(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPOSE_FILE", "other.yaml")
    monkeypatch.setenv("PGPORT", "9999")
    monkeypatch.setenv("PGPASSWORD", "synthetic-secret")
    env = provision._docker_environment(settings)
    assert env["PGPORT"] == settings["PGPORT"]
    assert "COMPOSE_FILE" not in env and "PGPASSWORD" not in env
    docker = MagicMock()
    monkeypatch.setattr(provision, "_docker", docker)
    provision._compose_up(settings, tmp_path)
    args = docker.call_args.args[0]
    assert "--no-recreate" in args and "--wait" in args
    assert "--remove-orphans" not in args and "--force-recreate" not in args
    assert args[-1] == "postgres"
    assert args[args.index("--project-name") + 1] == settings["COMPOSE_PROJECT_NAME"]


def test_s2_033_ready_setup_does_not_restart(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
) -> None:
    provision._manage("setup", settings, tmp_path)
    dependencies["_compose_up"].assert_not_called()
    dependencies["_create_identity"].assert_not_called()
    dependencies["_verify_identity"].assert_called_once()


def test_s2_034_port_conflict_prevents_provisioning(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
) -> None:
    dependencies["_target"].return_value = None
    dependencies["_require_port_available"].side_effect = ValueError("port unavailable")
    with pytest.raises(ValueError, match="port unavailable"):
        provision._manage("setup", settings, tmp_path)
    dependencies["_compose_up"].assert_not_called()
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()


def test_s2_035_identity_creation_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = MagicMock()
    verify = MagicMock()
    monkeypatch.setattr(provision, "_verify_identity", verify)
    provision._create_identity(connection, "staging")
    connection.transaction.assert_called_once()
    statements = connection.execute.call_args_list
    assert statements[0].args == (provision._IDENTITY_SQL,)
    assert "VALUES (TRUE, %s)" in statements[1].args[0]
    assert statements[1].args[1] == ("staging",)
    assert statements[2].args == (provision._IDENTITY_PROTECTION_SQL,)
    verify.assert_called_once_with(connection, "staging")


def test_s2_036_docker_failure_does_not_disclose_output(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock(returncode=1, stderr="synthetic-secret", stdout="synthetic-secret")
    monkeypatch.setattr(provision.subprocess, "run", MagicMock(return_value=result))
    with pytest.raises(ValueError, match="provisioning failed") as error:
        provision._docker(["compose", "up"], settings, tmp_path)
    assert "synthetic-secret" not in str(error.value)


def test_s2_037_other_container_port_conflict(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = dict(settings, POSTGRES_CONTAINER_NAME="other", COMPOSE_PROJECT_NAME="other",
                 POSTGRES_DATA_DIR=str(tmp_path / "other"))
    monkeypatch.setattr(provision, "_containers", lambda *_: [_container(other)])
    with pytest.raises(ValueError, match="port conflicts"):
        provision._target(settings, tmp_path)


def test_s2_038_reuse_stopped_container(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
) -> None:
    storage = Path(settings["POSTGRES_DATA_DIR"]) / "18" / "docker"
    storage.mkdir(parents=True)
    (storage / "PG_VERSION").write_text("18\n")
    stopped = _container(settings)
    stopped["State"]["Running"] = False
    dependencies["_target"].side_effect = [stopped, _container(settings)]
    provision._manage("setup", settings, tmp_path)
    dependencies["_compose_up"].assert_called_once()
    dependencies["_create_identity"].assert_not_called()
    dependencies["_verify_identity"].assert_called_once()


@pytest.mark.parametrize("failure", [False, True])
def test_s2_040_explicit_password_file_authentication(
    settings: dict[str, str], monkeypatch: pytest.MonkeyPatch, failure: bool,
) -> None:
    import sys
    from types import SimpleNamespace

    class DriverError(Exception):
        pass

    connection = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    if failure:
        connect.side_effect = DriverError("synthetic-secret")
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(
        connect=connect, Error=DriverError,
    ))
    monkeypatch.setattr(provision, "_require_client_environment", MagicMock())
    if failure:
        with pytest.raises(ValueError, match="password-file authentication") as error:
            with provision._connect(settings):
                pytest.fail("Invalid credentials accepted")
        assert "synthetic-secret" not in str(error.value)
    else:
        with provision._connect(settings) as actual:
            assert actual is connection
    connect.assert_called_once_with(
        host=settings["PGHOST"], hostaddr="127.0.0.1",
        port=settings["PGPORT"], dbname=settings["PGDATABASE"],
        user=settings["PGUSER"], passfile=settings["PGPASSFILE"],
        require_auth="scram-sha-256", connect_timeout=5, autocommit=True,
    )


@pytest.mark.parametrize("command", ["setup", "check"])
def test_s2_041_management_entry_point(
    settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], command: str,
) -> None:
    import runpy
    import sys

    load = MagicMock(return_value=settings)
    manage = MagicMock()
    monkeypatch.setattr(provision, "_load_settings", load)
    monkeypatch.setattr(provision, "_manage", manage)
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "manage_environment.py"
    monkeypatch.setattr(sys, "argv", [str(script), command])
    namespace = runpy.run_path(str(script))
    assert namespace["_main"]() == 0
    load.assert_called_once_with(root, prepare=command == "setup")
    manage.assert_called_once_with(command, settings, root)
    assert f"Environment {command} complete" in capsys.readouterr().out


@pytest.mark.parametrize(("entries", "expected"), [
    (b"# ignored\nlocalhost:5434:sample_test:sample_owner:secret\n", b"secret"),
    (b"other:5434:sample_test:sample_owner:wrong\n*:*:*:*:fallback\n", b"fallback"),
    (b"*:*:*:*:first\nlocalhost:5434:sample_test:sample_owner:second\n", b"first"),
    (b"localhost:5434:sample_test:sample_owner:a\\:b\\\\c\r\n", b"a:b\\c"),
    (b"localhost:5434:sample_test:sample_owner:a\\\n", b"a\\"),
    (b"localhost:5434:sample_test:sample_owner:a:b\n", b"a"),
    (b"\\*:*:*:*:wrong\n*:*:*:*:right\n", b"right"),
])
def test_s2_042_client_credential_selection(
    settings: dict[str, str], entries: bytes, expected: bytes,
) -> None:
    path = Path(settings["PGPASSFILE"])
    path.write_bytes(entries)
    assert provision._client_password(settings) == expected
    assert path.read_bytes() == entries


@pytest.mark.parametrize("entries", [
    b"# no credential\n",
    b"wrong:5434:sample_test:sample_owner:synthetic-secret\n",
    b"*:*:*:*:\n*:*:*:*:synthetic-secret\n",
    b"*:*:*:*:synthetic-secret\x00\n",
])
def test_s2_043_missing_client_credential_prevents_setup(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
    entries: bytes,
) -> None:
    path = Path(settings["PGPASSFILE"])
    path.write_bytes(entries)
    dependencies["_target"].return_value = None
    with pytest.raises(ValueError, match="PGPASSFILE") as error:
        provision._manage("setup", settings, tmp_path)
    assert "synthetic-secret" not in str(error.value)
    dependencies["_compose_up"].assert_not_called()
    dependencies["_require_local_docker"].assert_not_called()
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()
    assert path.read_bytes() == entries


@pytest.mark.parametrize("password", [
    b"wrong-secret\n", b"synthetic\nextra", b"\n", b"synthetic\r\n",
])
def test_s2_044_invalid_initial_password_prevents_setup(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
    password: bytes,
) -> None:
    path = Path(settings["POSTGRES_PASSWORD_FILE"])
    path.write_bytes(password)
    dependencies["_target"].return_value = None
    with pytest.raises(ValueError, match="password") as error:
        provision._manage("setup", settings, tmp_path)
    assert "wrong-secret" not in str(error.value)
    dependencies["_compose_up"].assert_not_called()
    dependencies["_create_identity"].assert_not_called()
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()
    assert path.read_bytes() == password


@pytest.mark.parametrize(("command", "state"), [
    ("setup", "running"), ("check", "running"),
    ("setup", "stopped"), ("setup", "container_removed"),
])
def test_s2_045_existing_cluster_uses_current_client_credential(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
    command: str, state: str,
) -> None:
    path = Path(settings["POSTGRES_PASSWORD_FILE"])
    path.write_bytes(b"old-password\n")
    storage = Path(settings["POSTGRES_DATA_DIR"]) / "18" / "docker"
    storage.mkdir(parents=True)
    marker = storage / "PG_VERSION"
    marker.write_text("18\n")
    if state == "stopped":
        stopped = _container(settings)
        stopped["State"]["Running"] = False
        dependencies["_target"].side_effect = [stopped, _container(settings)]
    elif state == "container_removed":
        dependencies["_target"].side_effect = [None, _container(settings)]
    provision._manage(command, settings, tmp_path)
    if state == "running":
        dependencies["_compose_up"].assert_not_called()
    else:
        dependencies["_compose_up"].assert_called_once()
    dependencies["_create_identity"].assert_not_called()
    dependencies["_verify_identity"].assert_called_once()
    assert path.read_bytes() == b"old-password\n"
    assert marker.read_text() == "18\n"


def test_s2_046_missing_driver_prevents_setup(
    tmp_path: Path, settings: dict[str, str], dependencies: dict[str, Any],
) -> None:
    dependencies["import_module"].side_effect = ImportError("driver missing")
    with pytest.raises(ImportError, match="driver missing"):
        provision._manage("setup", settings, tmp_path)
    dependencies["_require_local_docker"].assert_not_called()
    dependencies["_compose_up"].assert_not_called()
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()


def test_s2_047_escaped_matching_initial_credentials(
    settings: dict[str, str],
) -> None:
    client = Path(settings["PGPASSFILE"])
    initial = Path(settings["POSTGRES_PASSWORD_FILE"])
    client.write_bytes(b"localhost:5434:sample_test:sample_owner:a\\:b\\\\c\n")
    initial.write_bytes(b"a:b\\c\n")
    before = (client.read_bytes(), initial.read_bytes())
    provision._verify_initial_credentials(
        settings, provision._client_password(settings)
    )
    assert (client.read_bytes(), initial.read_bytes()) == before


@pytest.mark.parametrize("missing", ["both", "provisioning", "client"])
def test_s2_048_setup_prepares_directories_before_missing_credentials(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    for key, label in (("POSTGRES_PASSWORD_FILE", "provisioning"),
                       ("PGPASSFILE", "client")):
        original = Path(settings[key])
        path = tmp_path / label / "secrets" / "password"
        if missing in ("both", label):
            original.unlink()
        else:
            path.parent.mkdir(parents=True)
            original.rename(path)
        settings[key] = str(path)
    (root / ".env").write_text("\n".join(f"{k}={v}" for k, v in settings.items()))
    monkeypatch.setattr(provision, "_require_local_docker", MagicMock())
    monkeypatch.setattr(provision, "_target", MagicMock(return_value=None))
    monkeypatch.setattr(provision, "_require_port_available", MagicMock())
    up = MagicMock()
    monkeypatch.setattr(provision, "_compose_up", up)
    with pytest.raises(ValueError, match="Operator must supply") as error:
        provision._load_settings(root, prepare=True)
    storage = Path(settings["POSTGRES_DATA_DIR"])
    assert storage.is_dir()
    inode = storage.stat().st_ino
    assert stat.S_IMODE(storage.stat().st_mode) == 0o700
    for key, label in (("POSTGRES_PASSWORD_FILE", "provisioning"),
                       ("PGPASSFILE", "client")):
        path = Path(settings[key])
        assert path.parent.is_dir()
        if missing in ("both", label):
            assert not path.exists()
            assert str(path) in str(error.value)
            assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
            path.write_text("synthetic\n")
            path.chmod(0o600)
        else:
            assert str(path) not in str(error.value)
    before = {
        key: (Path(settings[key]).read_bytes(), Path(settings[key]).stat().st_mode,
              Path(settings[key]).parent.stat().st_mode)
        for key in ("POSTGRES_PASSWORD_FILE", "PGPASSFILE")
    }
    up.assert_not_called()
    assert provision._load_settings(root, prepare=True) == settings
    assert storage.stat().st_ino == inode
    assert before == {
        key: (Path(settings[key]).read_bytes(), Path(settings[key]).stat().st_mode,
              Path(settings[key]).parent.stat().st_mode)
        for key in before
    }
    up.assert_not_called()


@pytest.mark.parametrize("problem", ["read_only", "invalid_path", "conflict"])
def test_s2_049_directory_preparation_safety(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
    problem: str,
) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    password = tmp_path / "secrets" / "password"
    settings["POSTGRES_PASSWORD_FILE"] = str(password)
    if problem == "invalid_path":
        settings["POSTGRES_PASSWORD_FILE"] = str(root / "secrets" / "password")
    (root / ".env").write_text("\n".join(f"{k}={v}" for k, v in settings.items()))
    local = MagicMock()
    monkeypatch.setattr(provision, "_require_local_docker", local)
    monkeypatch.setattr(provision, "_target", MagicMock(side_effect=ValueError("conflict")))
    with pytest.raises(ValueError):
        provision._load_settings(root, prepare=problem != "read_only")
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()
    assert not password.parent.exists()
    assert not (root / "secrets").exists()
    if problem != "conflict":
        local.assert_not_called()


def test_s2_050_prepare_rejects_unrelated_mount(
    tmp_path: Path, settings: dict[str, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    other = dict(
        settings, POSTGRES_CONTAINER_NAME="other", COMPOSE_PROJECT_NAME="other",
        POSTGRES_DATA_DIR=str(unrelated), PGPORT="5433",
    )
    settings["POSTGRES_PASSWORD_FILE"] = str(unrelated / "secrets" / "password")
    (root / ".env").write_text("\n".join(f"{k}={v}" for k, v in settings.items()))
    monkeypatch.setattr(provision, "_require_local_docker", MagicMock())
    monkeypatch.setattr(provision, "_containers", lambda *_: [_container(other)])
    with pytest.raises(ValueError, match="Directory preparation overlaps"):
        provision._load_settings(root, prepare=True)
    assert not (unrelated / "secrets").exists()
    assert not Path(settings["POSTGRES_DATA_DIR"]).exists()

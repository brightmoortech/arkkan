"""Application database migrations and their catalog checks."""

import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._migration_workflow import _Migration

if TYPE_CHECKING:
    from psycopg import Connection

# An explicit, fixed catalog contract. No caller-provided SQL identifiers.
# Defaults and check predicates use PostgreSQL 18's catalog expression form.
_TABLES = {
    "resource_types": (
        ("type_id", "uuid", True, "gen_random_uuid()"),
        ("slug", "text", True, None),
        ("description", "text", False, None),
        ("is_system", "boolean", True, None),
    ),
    "resource_definitions": (
        ("resource_id", "uuid", True, "gen_random_uuid()"),
        ("name", "text", False, None),
        ("slug", "text", True, None),
        ("description", "text", False, None),
        ("type_id", "uuid", True, None),
    ),
    "resource_versions": (
        ("version_id", "uuid", True, "gen_random_uuid()"),
        ("resource_id", "uuid", True, None),
        ("version", "text", True, None),
        ("state", "text", True, None),
        ("content", "text", True, "''::text"),
        ("version_info", "text", False, None),
        ("created_at", "timestamp with time zone", True, "CURRENT_TIMESTAMP"),
    ),
}
_CONSTRAINTS = {
    "resource_types": {
        "resource_types_pkey": "PRIMARY KEY (type_id)",
        "resource_types_slug_key": "UNIQUE (slug)",
        "resource_types_slug_nonblank": "CHECK ((slug ~ '[^[:space:]]'::text))",
    },
    "resource_definitions": {
        "resource_definitions_pkey": "PRIMARY KEY (resource_id)",
        "resource_definitions_slug_key": "UNIQUE (slug)",
        "resource_definitions_type_id_fkey":
            "FOREIGN KEY (type_id) REFERENCES arkkan.resource_types(type_id)",
        "resource_definitions_slug_nonblank": "CHECK ((slug ~ '[^[:space:]]'::text))",
    },
    "resource_versions": {
        "resource_versions_pkey": "PRIMARY KEY (version_id)",
        "resource_versions_resource_id_version_key": "UNIQUE (resource_id, version)",
        "resource_versions_resource_id_fkey":
            "FOREIGN KEY (resource_id) REFERENCES arkkan.resource_definitions(resource_id)",
        "resource_versions_version_nonblank": "CHECK ((version ~ '[^[:space:]]'::text))",
        "resource_versions_valid_state": (
            "CHECK ((state = ANY (ARRAY['enabled'::text, 'enabled_default'::text, "
            "'disabled'::text, 'obsolete'::text])))"
        ),
    },
}
_INDEXES = {
    "resource_types": {
        "resource_types_pkey": "type_id",
        "resource_types_slug_key": "slug",
    },
    "resource_definitions": {
        "resource_definitions_pkey": "resource_id",
        "resource_definitions_slug_key": "slug",
    },
    "resource_versions": {
        "resource_versions_pkey": "version_id",
        "resource_versions_resource_id_version_key": "resource_id, version",
    },
}
_DEFAULT_INDEX = "resource_versions_one_default"
_SEED_SLUGS = frozenset((
    "constraints", "process", "rubric", "role", "task", "templates", "extensions",
))


# Each function is checked independently, including its argument names and types.
_API_HELPERS = (
    ("api_response", "plpgsql", (("operation_name", "text"), ("result", "text"),
                                 ("data", "jsonb"), ("reason", "text")), "jsonb"),
    ("api_identifier_valid", "sql", (("value", "text"),), "boolean"),
    ("api_state_valid", "sql", (("value", "text"),), "boolean"),
    ("api_mode_valid", "sql", (("value", "text"),), "boolean"),
)


# WP2 functions remain owner-only until the access-grant work package. Defaults
# use PostgreSQL's catalog expression form, not the spelling in the SQL file.
_API_WRITES = (
    ("add_resource_type", (("slug", "text"), ("description", "text")), "NULL::text"),
    ("update_resource_type", (("slug", "text"), ("description", "text")), None),
    ("delete_resource_type", (("slug", "text"),), None),
    ("add_resource", tuple((name, "text") for name in (
        "slug", "version", "type_slug", "name", "description", "content", "version_info", "state",
    )), "NULL::text, NULL::text, NULL::text, ''::text, NULL::text, 'disabled'::text"),
    ("update_resource", (("slug", "text"), ("changes", "jsonb"), ("version", "text")), "NULL::text"),
)


def _role_ready(connection: "Connection[Any]", role: str) -> bool:
    row = connection.execute("""
        SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
               rolreplication, rolbypassrls, rolinherit,
               EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members
                       WHERE member = r.oid)
        FROM pg_catalog.pg_roles AS r WHERE rolname = %s
    """, (role,)).fetchone()
    if row is None:
        return False
    if row != (True, False, False, False, False, False, True, False):
        raise ValueError(f"Conflicting attributes or inherited privileges on role {role}.")
    return True


def _schema_ready(connection: "Connection[Any]", schema: str) -> bool:
    row = connection.execute("""
        SELECT pg_catalog.pg_get_userbyid(nspowner) = CURRENT_USER,
               NOT EXISTS (
                   SELECT 1 FROM pg_catalog.aclexplode(COALESCE(
                       nspacl, pg_catalog.acldefault('n', nspowner))) AS acl
                   WHERE acl.grantee <> nspowner
               )
        FROM pg_catalog.pg_namespace WHERE nspname = %s
    """, (schema,)).fetchone()
    if row is None:
        return False
    if row != (True, True):
        raise ValueError(f"Conflicting owner or access privileges on schema {schema}.")
    allowed_relations = {}
    if schema == "arkkan":
        allowed_relations = {table: "r" for table in _TABLES}
        allowed_relations.update({
            index: "i" for indexes in _INDEXES.values() for index in indexes
        })
        allowed_relations[_DEFAULT_INDEX] = "i"
    relations = connection.execute("""
        SELECT c.relname, c.relkind FROM pg_catalog.pg_class AS c
        JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = %s
    """, (schema,)).fetchall()
    if any(allowed_relations.get(name) != kind for name, kind in relations):
        raise ValueError(f"Unexpected relation in schema {schema}.")
    allowed_helpers = {(f"reject_{table}_change", 0) for table in _TABLES}
    allowed_helpers.update((name, len(arguments)) for name, _, arguments, _ in _API_HELPERS)
    if schema == "arkkan_api":
        allowed_helpers = {(name, len(arguments)) for name, arguments, _ in _API_WRITES}
    functions = connection.execute("""
        SELECT p.proname, p.pronargs FROM pg_catalog.pg_proc AS p
        JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
        WHERE n.nspname = %s
    """, (schema,)).fetchall()
    if any((name, count) not in allowed_helpers for name, count in functions):
        raise ValueError(f"Unexpected function in schema {schema}.")
    return True


def _relation(connection: "Connection[Any]", name: str) -> int | None:
    row = connection.execute(
        """SELECT c.oid FROM pg_catalog.pg_class AS c
        JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'arkkan' AND c.relname = %s""", (name,)
    ).fetchone()
    return row[0] if row is not None else None


def _table_ready(connection: "Connection[Any]", table: str) -> bool:
    oid = _relation(connection, table)
    if oid is None:
        # A same-named type would prevent creation of the table's row type.
        collision = connection.execute(
            """SELECT EXISTS (
                SELECT 1 FROM pg_catalog.pg_type AS t
                JOIN pg_catalog.pg_namespace AS n ON n.oid = t.typnamespace
                WHERE n.nspname = 'arkkan' AND t.typname = %s
            )""", (table,)
        ).fetchone()[0]
        if collision:
            raise ValueError(f"Conflicting type name for arkkan.{table}.")
        if any(_relation(connection, name) is not None for name in _INDEXES[table]):
            raise ValueError(f"Conflicting index name for missing table arkkan.{table}.")
        return False
    row = connection.execute("""
        SELECT relkind, relpersistence,
               pg_catalog.pg_get_userbyid(relowner) = CURRENT_USER,
               relrowsecurity, relforcerowsecurity, relispartition,
               NOT EXISTS (SELECT 1 FROM pg_catalog.pg_inherits
                           WHERE inhrelid = c.oid OR inhparent = c.oid),
               NOT EXISTS (
                   SELECT 1 FROM pg_catalog.aclexplode(COALESCE(
                       relacl, pg_catalog.acldefault('r', relowner))) AS acl
                   WHERE acl.grantee <> relowner
               )
        FROM pg_catalog.pg_class AS c WHERE oid = %s
    """, (oid,)).fetchone()
    if row != ("r", "p", True, False, False, False, True, True):
        raise ValueError(f"Conflicting table type, owner or privileges on arkkan.{table}.")
    columns = connection.execute("""
        SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod),
               a.attnotnull, pg_catalog.pg_get_expr(d.adbin, d.adrelid),
               a.attidentity, a.attgenerated, a.attisdropped,
               a.attcollation = t.typcollation, a.attacl IS NULL
        FROM pg_catalog.pg_attribute AS a
        JOIN pg_catalog.pg_type AS t ON t.oid = a.atttypid
        LEFT JOIN pg_catalog.pg_attrdef AS d
            ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = %s AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
    """, (oid,)).fetchall()
    expected_columns = [(*column, "", "", False, True, True) for column in _TABLES[table]]
    if columns != expected_columns:
        raise ValueError(f"Conflicting column definitions on arkkan.{table}.")
    constraints = connection.execute("""
        SELECT conname, pg_catalog.pg_get_constraintdef(oid),
               convalidated, conenforced, condeferrable, condeferred
        FROM pg_catalog.pg_constraint
        WHERE conrelid = %s AND contype <> 'n'
    """, (oid,)).fetchall()
    if (
        {name: definition for name, definition, *_ in constraints} != _CONSTRAINTS[table]
        or any(flags != [True, True, False, False]
               for _, _, *flags in constraints)
    ):
        raise ValueError(f"Conflicting constraints on arkkan.{table}.")
    # PostgreSQL 18 stores NOT NULL constraints separately; attnotnull is
    # insufficient if a constraint has not been validated or enforced.
    invalid_not_null = connection.execute("""
        SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint
                       WHERE conrelid = %s AND contype = 'n'
                         AND (NOT convalidated OR NOT conenforced))
    """, (oid,)).fetchone()[0]
    if invalid_not_null:
        raise ValueError(f"Unvalidated NOT NULL constraint on arkkan.{table}.")
    disabled_constraints = connection.execute("""
        SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_trigger
                       WHERE tgrelid = %s AND tgisinternal
                       AND tgenabled NOT IN ('O', 'A'))
    """, (oid,)).fetchone()[0]
    if disabled_constraints:
        raise ValueError(f"Disabled constraint trigger on arkkan.{table}.")
    indexes = _index_rows(connection, oid)
    expected_indexes = {
        name: f"CREATE UNIQUE INDEX {name} ON arkkan.{table} USING btree ({keys})"
        for name, keys in _INDEXES[table].items()
    }
    if table == "resource_versions" and _DEFAULT_INDEX in indexes:
        expected_indexes[_DEFAULT_INDEX] = _default_index_definition()
    if indexes != expected_indexes:
        raise ValueError(f"Conflicting index definitions on arkkan.{table}.")
    return True


def _index_rows(connection: "Connection[Any]", oid: int) -> dict[str, str]:
    rows = connection.execute("""
        SELECT c.relname, pg_catalog.pg_get_indexdef(i.indexrelid),
               i.indisvalid, i.indisready, i.indislive, i.indimmediate
        FROM pg_catalog.pg_index AS i
        JOIN pg_catalog.pg_class AS c ON c.oid = i.indexrelid
        WHERE i.indrelid = %s
    """, (oid,)).fetchall()
    if any(flags != [True, True, True, True] for _, _, *flags in rows):
        raise ValueError("An existing index is invalid, not ready or not immediate.")
    return {name: definition for name, definition, *_ in rows}


def _default_index_definition() -> str:
    return (
        "CREATE UNIQUE INDEX resource_versions_one_default ON arkkan.resource_versions "
        "USING btree (resource_id) WHERE (state = 'enabled_default'::text)"
    )


def _default_index_ready(connection: "Connection[Any]") -> bool:
    index = _relation(connection, _DEFAULT_INDEX)
    table = _relation(connection, "resource_versions")
    if index is None:
        if table is not None and connection.execute("""
            SELECT EXISTS (
                SELECT resource_id FROM arkkan.resource_versions
                WHERE state = 'enabled_default' GROUP BY resource_id
                HAVING count(*) > 1
            )
        """).fetchone()[0]:
            raise ValueError("Conflicting default versions prevent creation of the unique index.")
        return False
    if table is None or _index_rows(connection, table).get(_DEFAULT_INDEX) != _default_index_definition():
        raise ValueError(f"Conflicting index {_DEFAULT_INDEX}.")
    return True


def _trigger_ready(
    connection: "Connection[Any]", table: str, body: str,
) -> bool:
    helper = f"reject_{table}_change"
    trigger = f"protect_{table}_immutable"
    rows = connection.execute("""
        SELECT p.prosrc, p.prokind, p.prorettype = 'pg_catalog.trigger'::regtype,
               l.lanname, pg_catalog.pg_get_userbyid(p.proowner) = CURRENT_USER,
               p.prosecdef, p.provolatile, p.proisstrict, p.proparallel,
               p.proconfig,
               NOT EXISTS (
                   SELECT 1 FROM pg_catalog.aclexplode(COALESCE(
                       p.proacl, pg_catalog.acldefault('f', p.proowner))) AS acl
                   WHERE acl.grantee <> p.proowner
               )
        FROM pg_catalog.pg_proc AS p
        JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
        JOIN pg_catalog.pg_language AS l ON l.oid = p.prolang
        WHERE n.nspname = 'arkkan' AND p.proname = %s AND p.pronargs = 0
    """, (helper,)).fetchall()
    if rows and rows != [(body, "f", True, "plpgsql", True, False, "v", False,
                          "u", ["search_path=pg_catalog"], True)]:
        raise ValueError(f"Conflicting integrity helper arkkan.{helper}.")
    oid = _relation(connection, table)
    if oid is None:
        return False
    triggers = connection.execute("""
        SELECT tgname, tgtype, tgenabled,
               tgfoid = pg_catalog.to_regprocedure(%s),
               tgattr::text, tgqual IS NULL, tgnargs, tgconstraint = 0
        FROM pg_catalog.pg_trigger
        WHERE tgrelid = %s AND NOT tgisinternal
    """, (f"arkkan.{helper}()", oid)).fetchall()
    if not triggers:
        return False
    if not rows or triggers != [(trigger, 19, "A", True, "", True, 0, True)]:
        raise ValueError(f"Conflicting integrity trigger on arkkan.{table}.")
    return True


def _seed_ready(connection: "Connection[Any]", seeds: dict[str, str]) -> bool:
    if _relation(connection, "resource_types") is None:
        return False
    rows = connection.execute("""
        SELECT slug, is_system FROM arkkan.resource_types
        WHERE is_system OR slug = ANY(%s::text[])
    """, (list(seeds),)).fetchall()
    if any(slug not in seeds or not is_system for slug, is_system in rows):
        raise ValueError("Conflicting system resource type flag or unexpected protected type.")
    return {slug for slug, _ in rows} == set(seeds)


def _execute_sql(connection: "Connection[Any]", statement: str) -> None:
    connection.execute(statement)


def _apply_seeds(
    connection: "Connection[Any]", seeds: dict[str, str], statement: str,
) -> None:
    for slug, description in seeds.items():
        # A conflicting existing flag is rejected by the check. Existing
        # descriptions are intentionally never updated, including NULL.
        inserted = connection.execute(
            statement + "\nRETURNING description", (slug, description)
        ).fetchone()
        if inserted is not None and inserted[0] != description:
            raise ValueError("A newly inserted system type has an unexpected description.")


def _api_function_ready(
    connection: "Connection[Any]", *, name: str, language: str,
    arguments: tuple[tuple[str, str], ...], return_type: str, body: str,
    schema: str = "arkkan", defaults: str | None = None,
) -> bool:
    rows = connection.execute("""
        SELECT p.prosrc, p.prokind, pg_catalog.pg_get_userbyid(p.proowner) = CURRENT_USER,
               l.lanname, pg_catalog.oidvectortypes(p.proargtypes), p.proargnames,
               pg_catalog.format_type(p.prorettype, NULL),
               p.proretset, p.prosecdef, p.provolatile, p.proisstrict,
               p.proparallel, p.proconfig, p.pronargdefaults,
               p.proargmodes IS NULL, p.provariadic = 0, p.proleakproof,
               pg_catalog.pg_get_expr(p.proargdefaults, 0),
               NOT EXISTS (
                   SELECT 1 FROM pg_catalog.aclexplode(COALESCE(
                       p.proacl, pg_catalog.acldefault('f', p.proowner))) AS acl
                   WHERE acl.grantee <> p.proowner
               )
        FROM pg_catalog.pg_proc AS p
        JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
        JOIN pg_catalog.pg_language AS l ON l.oid = p.prolang
        WHERE n.nspname = %s AND p.proname = %s
    """, (schema, name)).fetchall()
    if not rows:
        return False
    expected = (body, "f", True, language, ", ".join(kind for _, kind in arguments),
                [argument for argument, _ in arguments], return_type,
                False, schema == "arkkan_api", "v" if schema == "arkkan_api" else "i",
                False, "u", ["search_path=pg_catalog"],
                0 if defaults is None else len(defaults.split(", ")),
                True, True, False, defaults, True)
    if rows != [expected]:
        raise ValueError(f"Conflicting API function {schema}.{name}.")
    return True


def _migration_list(root: Path) -> tuple[_Migration, ...]:
    folder = root / "sql" / "migrations"
    migrations: list[_Migration] = []

    def _add(filename: str, check: Callable[["Connection[Any]"], bool]) -> str:
        statement = (folder / f"{filename}.sql").read_text(encoding="utf-8")
        migrations.append(_Migration(filename, check, partial(_execute_sql, statement=statement)))
        return statement

    for number, role in enumerate(("arkkan_admin", "arkkan_user"), 1):
        _add(f"{number:03}_{role}", partial(_role_ready, role=role))
    for number, schema in enumerate(("arkkan", "arkkan_api"), 3):
        _add(f"{number:03}_{schema}", partial(_schema_ready, schema=schema))
    for number, table in enumerate(_TABLES, 5):
        _add(f"{number:03}_{table}", partial(_table_ready, table=table))
    _add("008_default_index", _default_index_ready)
    for number, table in enumerate(_TABLES, 9):
        filename = f"{number:03}_{table}_immutability"
        statement = (folder / f"{filename}.sql").read_text(encoding="utf-8")
        parts = statement.split("$body$")
        if len(parts) != 3 or not parts[1].strip():
            raise ValueError(f"Invalid integrity helper migration: {filename}.")
        body = parts[1]
        migrations.append(_Migration(
            filename, partial(_trigger_ready, table=table, body=body),
            partial(_execute_sql, statement=statement),
        ))
    seeds = json.loads((folder / "012_resource_types.json").read_text(encoding="utf-8"))
    if (
        not isinstance(seeds, dict) or set(seeds) != _SEED_SLUGS
        or any(not isinstance(value, str) or not value for value in seeds.values())
    ):
        raise ValueError("Invalid protected resource-type seed manifest.")
    seed_sql = (folder / "012_seed_resource_types.sql").read_text(encoding="utf-8").strip().removesuffix(";")
    migrations.append(_Migration(
        "012_seed_resource_types", partial(_seed_ready, seeds=seeds),
        partial(_apply_seeds, seeds=seeds, statement=seed_sql),
    ))
    for number, (name, language, arguments, return_type) in enumerate(_API_HELPERS, 13):
        filename = f"{number:03}_{name}"
        statement = (folder / f"{filename}.sql").read_text(encoding="utf-8")
        parts = statement.split("$body$")
        if len(parts) != 3 or not parts[1].strip():
            raise ValueError(f"Invalid API helper migration: {filename}.")
        migrations.append(_Migration(
            filename, partial(_api_function_ready, name=name, language=language,
                              arguments=arguments, return_type=return_type, body=parts[1]),
            partial(_execute_sql, statement=statement),
        ))
    for number, (name, arguments, defaults) in enumerate(_API_WRITES, 17):
        filename = f"{number:03}_{name}"
        statement = (folder / f"{filename}.sql").read_text(encoding="utf-8")
        parts = statement.split("$body$")
        if len(parts) != 3 or not parts[1].strip():
            raise ValueError(f"Invalid API function migration: {filename}.")
        migrations.append(_Migration(
            filename, partial(_api_function_ready, name=name, language="plpgsql",
                              arguments=arguments, return_type="jsonb", body=parts[1],
                              schema="arkkan_api", defaults=defaults),
            partial(_execute_sql, statement=statement),
        ))
    return tuple(migrations)

"""Command-line parsing and presentation through the public Python API."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import arkkan


def _metadata_option(
    parser: argparse.ArgumentParser, flag: str, field: str,
    clear_option: str, *, required: bool = False,
) -> None:
    options = parser.add_mutually_exclusive_group(required=required)
    options.add_argument(
        flag, dest=field, default=argparse.SUPPRESS, metavar=field.upper(),
    )
    options.add_argument(
        clear_option, dest=field, action="store_const", const=None,
        default=argparse.SUPPRESS, help=f"Clear {field} (set to null)",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkkan", allow_abbrev=False,
        description="Manage and retrieve versioned prompt resources.",
        epilog="Uses libpq environment settings and password-file authentication.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    resource = groups.add_parser(
        "resource", help="Manage resources and retrieve content", allow_abbrev=False,
    )
    commands = resource.add_subparsers(dest="command", required=True)
    for name, description in (
        ("get", "Retrieve content (default version when -v is omitted)"),
        ("list", "List resource metadata for a type"),
        ("default", "Identify a resource's default version"),
        ("info", "Show resource metadata and all version states"),
    ):
        command = commands.add_parser(
            name, help=description, description=description, allow_abbrev=False,
        )
        command.add_argument("-j", action="store_true", help="Print API response JSON")
        if name == "list":
            command.add_argument("-t", dest="type_slug", required=True, metavar="TYPE")
        else:
            command.add_argument("slug", metavar="SLUG")
        if name == "get":
            command.add_argument("-v", dest="version", metavar="VERSION")
            command.add_argument(
                "-m", dest="mode", metavar="MODE",
                choices=("strict", "version_priority", "default_priority"),
                help="Selection mode (requires -v): %(choices)s",
            )
    add = commands.add_parser(
        "add", help="Create a resource version", allow_abbrev=False,
        description="Create a version; type is required for a new resource.",
    )
    add.add_argument("slug", metavar="SLUG")
    add.add_argument("version", metavar="VERSION")
    add.add_argument("-t", dest="type_slug", metavar="TYPE")
    add.add_argument("-n", dest="name", metavar="NAME")
    add.add_argument("-d", dest="description", metavar="DESCRIPTION")
    add.add_argument("-i", dest="version_info", metavar="VERSION_INFO")
    add.add_argument("-s", dest="state", default="disabled", metavar="STATE")
    add.add_argument(
        "-f", dest="file", metavar="FILE",
        help="UTF-8 content file, or - for stdin; omitted means empty content",
    )
    add.add_argument("-j", action="store_true", help="Print API response JSON")

    update = commands.add_parser(
        "update", help="Update resource or version metadata", allow_abbrev=False,
        description="Update metadata; -i/--clear-info requires -v and vice versa.",
    )
    update.add_argument("slug", metavar="SLUG")
    update.add_argument("-v", dest="version", metavar="VERSION")
    _metadata_option(update, "-n", "name", "--clear-name")
    _metadata_option(update, "-d", "description", "--clear-description")
    _metadata_option(update, "-i", "version_info", "--clear-info")
    update.add_argument("-j", action="store_true", help="Print API response JSON")

    for name, description in (
        ("delete-version", "Delete one obsolete version, keeping its resource"),
        ("delete-obsolete", "Delete a resource's obsolete versions"),
        ("cleanup", "Delete obsolete versions across all resources"),
        ("delete", "Delete an empty or entirely obsolete resource"),
        ("state", "Change one version's lifecycle state"),
        ("state-all", "Change all versions' lifecycle state atomically"),
        ("state-matching", "Change versions matching a source state atomically"),
    ):
        command = commands.add_parser(
            name, help=description, description=description, allow_abbrev=False,
        )
        command.add_argument("-j", action="store_true", help="Print API response JSON")
        if name != "cleanup":
            command.add_argument("slug", metavar="SLUG")
        if name in ("delete-version", "state"):
            command.add_argument("-v", dest="version", required=True, metavar="VERSION")
        if name in ("state", "state-all", "state-matching"):
            command.add_argument("-s", dest="target_state", required=True, metavar="STATE")
        if name == "state-matching":
            command.add_argument("-g", dest="source_state", required=True, metavar="STATE")
        if name == "state":
            command.add_argument(
                "-F", dest="force", action="store_true",
                help="Permit default removal without replacement; other policies still apply",
            )

    resource_type = groups.add_parser(
        "type", help="Manage resource types", allow_abbrev=False,
    )
    type_commands = resource_type.add_subparsers(dest="command", required=True)
    for name in ("add", "update", "delete"):
        command = type_commands.add_parser(
            name, help=f"{name.capitalize()} a resource type", allow_abbrev=False,
        )
        command.add_argument("slug", metavar="TYPE")
        command.add_argument("-j", action="store_true", help="Print API response JSON")
        if name == "add":
            command.add_argument("-d", dest="description", metavar="DESCRIPTION")
        elif name == "update":
            _metadata_option(
                command, "-d", "description", "--clear-description", required=True,
            )
    return parser


def _content(filename: str | None) -> str:
    if filename is None:
        return ""
    # Decode bytes explicitly: stdin's locale encoding and universal-newline
    # translation must not change the supplied UTF-8 content.
    try:
        if filename == "-":
            content = sys.stdin.buffer.read()
        else:
            content = Path(filename).read_bytes()
    except (OSError, ValueError) as error:
        raise ValueError(
            "Cannot read content; check the file or standard input."
        ) from error
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Content must be valid UTF-8.") from error


def _write_response(
    args: argparse.Namespace, parser: argparse.ArgumentParser,
) -> dict[str, Any]:
    if args.group == "type":
        if args.command == "add":
            return arkkan.add_resource_type(args.slug, args.description)
        return arkkan.update_resource_type(args.slug, args.description)
    if args.command == "add":
        try:
            content = _content(args.file)
        except ValueError as error:
            parser.error(str(error))
        return arkkan.add_resource(
            args.slug, args.version, type_slug=args.type_slug, name=args.name,
            description=args.description, content=content,
            version_info=args.version_info, state=args.state,
        )
    changes = {
        field: getattr(args, field)
        for field in ("name", "description", "version_info")
        if hasattr(args, field)
    }
    if not changes:
        parser.error("supply at least one metadata update")
    if ("version_info" in changes) != (args.version is not None):
        parser.error("-i/--clear-info requires -v and vice versa")
    return arkkan.update_resource(args.slug, changes, version=args.version)


def _read_response(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "get":
        if args.version is None:
            return arkkan.get_resource_content(args.slug)
        if args.mode is None:
            return arkkan.get_resource_content(args.slug, args.version)
        return arkkan.get_resource_content(args.slug, args.version, args.mode)
    if args.command == "list":
        return arkkan.list_resources_matching_type(args.type_slug)
    if args.command == "default":
        return arkkan.get_resource_version_default(args.slug)
    if args.command == "info":
        return arkkan.get_resource_info(args.slug)
    raise ValueError("Unsupported read command.")


def _lifecycle_response(args: argparse.Namespace) -> dict[str, Any]:
    if args.group == "type" and args.command == "delete":
        return arkkan.delete_resource_type(args.slug)
    if args.command == "delete-version":
        return arkkan.delete_resource_version(args.slug, args.version)
    if args.command == "delete-obsolete":
        return arkkan.delete_resource_version_all(args.slug)
    if args.command == "cleanup":
        return arkkan.clean_up()
    if args.command == "delete":
        return arkkan.delete_resource(args.slug)
    if args.command == "state":
        return arkkan.set_resource_state(
            args.slug, args.version, args.target_state, force=args.force,
        )
    if args.command == "state-all":
        return arkkan.set_resource_state_all(args.slug, args.target_state)
    if args.command == "state-matching":
        return arkkan.set_resource_state_all_with_guard(
            args.slug, args.source_state, args.target_state,
        )
    raise ValueError("Unsupported lifecycle command.")


def _print_result(response: dict[str, Any], json_output: bool) -> int:
    failed = response["result"] == "error"
    if json_output:
        print(json.dumps(response, ensure_ascii=False))
    elif failed:
        print(f"arkkan: {response['reason']}", file=sys.stderr)
    else:
        data = response["data"]
        operation = response["operation_name"]
        if operation == "get_resource_content":
            # Preserve content exactly, including empty content and final newlines.
            sys.stdout.write(data["content"])
        elif operation == "list_resources_matching_type":
            if not data:
                print("No resources found.")
            for item in data:
                print(f"{item['slug']}: {item['name'] or ''}")
                if item["description"] is not None:
                    print(f"  Description: {item['description']}")
        elif operation == "get_resource_version_default":
            print(f"{data['slug']}: {data['version']}")
        elif operation == "get_resource_info":
            print(f"Resource: {data['slug']}")
            print(f"Type: {data['type_slug']}")
            print(f"Name: {data['name'] if data['name'] is not None else '(unset)'}")
            description = data["description"]
            print(f"Description: {description if description is not None else '(unset)'}")
            print("Versions:")
            for version in data["versions"]:
                print(
                    f"  {version['version']}: {version['state']} "
                    f"({version['created_at']})"
                )
            if not data["versions"]:
                print("  None")
        elif operation == "add_resource":
            print(f"Created {data['slug']} version {data['version']}: {data['state']}")
        elif operation == "update_resource":
            target = data["slug"]
            if "version" in data:
                target += f" version {data['version']}"
            print(f"Updated {target}: {', '.join(data['updated_fields'])}")
        elif operation == "add_resource_type":
            print(f"Created type: {data['slug']}")
        elif operation == "update_resource_type":
            print(f"Updated type description: {data['slug']}")
        elif operation == "delete_resource_type":
            print(f"Deleted type: {data['slug']}")
        elif operation == "delete_resource_version":
            print(f"Deleted {data['slug']} version {data['version']}")
        elif operation == "delete_resource_version_all":
            print(f"Deleted obsolete versions for {data['slug']}: {data['deleted_count']}")
        elif operation == "clean_up":
            print(f"Deleted obsolete versions: {data['deleted_count']}")
        elif operation == "delete_resource":
            print(f"Deleted resource {data['slug']}; versions: {data['deleted_version_count']}")
        elif operation == "set_resource_state":
            print(f"Updated {data['slug']} version {data['version']}: {data['state']}")
        elif operation in ("set_resource_state_all", "set_resource_state_all_with_guard"):
            print(f"Updated versions for {data['slug']}: {data['changed_count']}")
        else:
            raise ValueError("Unsupported operation output.")
    return 1 if failed else 0


def _main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "get" and args.mode is not None and args.version is None:
        parser.error("-m requires -v")
    if args.command in ("add", "update"):
        response = _write_response(args, parser)
    elif args.command in ("get", "list", "default", "info"):
        response = _read_response(args)
    else:
        response = _lifecycle_response(args)
    return _print_result(response, args.j)

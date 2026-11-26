"""Command-line parsing and presentation through the public Python API."""

import argparse
import json
import sys
from typing import Any

import arkkan


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arkkan", allow_abbrev=False,
        description="Manage and retrieve versioned prompt resources.",
        epilog="Uses libpq environment settings and password-file authentication.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    resource = groups.add_parser(
        "resource", help="Retrieve resources and metadata", allow_abbrev=False,
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
    # The namespace exists now; administration commands arrive in WP2.
    resource_type = groups.add_parser(
        "type", help="Resource type administration (pending)", allow_abbrev=False,
        description="Resource type administration commands are not yet implemented.",
    )
    resource_type.set_defaults(command=None)
    return parser


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
        else:
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
    return 1 if failed else 0


def _main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.group == "type":
        parser.error("resource type administration commands are not yet implemented")
    if args.command == "get" and args.mode is not None and args.version is None:
        parser.error("-m requires -v")
    return _print_result(_read_response(args), args.j)

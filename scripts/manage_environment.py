#!/usr/bin/env python3
"""Provision or check the configured local PostgreSQL environment."""

import argparse
import logging
from pathlib import Path

from arkkan._provisioning import _load_settings, _manage


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="Provision or start and verify PostgreSQL.")
    commands.add_parser("check", help="Verify the environment without changes.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    root = Path(__file__).resolve().parents[1]
    try:
        settings = _load_settings(root, prepare=args.command == "setup")
        _manage(args.command, settings, root)
    except ValueError as error:
        logging.error("%s", error)
        return 1
    except OSError:
        logging.error("Cannot access configured storage; inspect its path and permissions.")
        return 1
    except ImportError:
        logging.error("PostgreSQL driver unavailable; run the project bootstrap.")
        return 1
    print(f"[OK] Environment {args.command} complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

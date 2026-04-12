"""CLI entry point for disk_free."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .formatter import format_table
from .scanner import scan_subdirs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="disk_free",
        description="List subdirectory sizes.",
    )
    sub = parser.add_subparsers(dest="command")

    ls_parser = sub.add_parser("ls", help="List subdirectory sizes")
    ls_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "ls":
        target = Path(args.path).expanduser().resolve()
        if not target.is_dir():
            print(f"disk_free: not a directory: {target}", file=sys.stderr)
            sys.exit(1)

        entries = scan_subdirs(target)
        print(format_table(entries))

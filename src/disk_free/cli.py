"""CLI entry point for disk_free."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import shutil

from .artifacts import clean_artifacts, find_artifacts
from .formatter import format_artifacts_table, format_category_results, format_table, format_tree, human_size
from .inspect import deep_scan
from .progress import (
    finish_remove,
    finish_scan,
    finish_system_scan,
    print_dir_remove_progress,
    print_remove_progress,
    print_scan_progress,
    print_system_scan_progress,
)
from .scanner import scan_subdirs
from .system import DEFAULT_CATEGORIES, scan_categories


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

    art_parser = sub.add_parser("artifacts", help="Find removable build artifacts")
    art_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    art_parser.add_argument(
        "--clean",
        action="store_true",
        help="Prompt to remove found artifacts",
    )

    inspect_parser = sub.add_parser("inspect", help="Deep scan — drill into large directories")
    inspect_parser.add_argument(
        "path",
        nargs="?",
        default="~/Library",
        help="Directory to scan (default: ~/Library)",
    )
    inspect_parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="How many levels deep to drill (default: 3)",
    )
    inspect_parser.add_argument(
        "--min",
        type=str,
        default="500M",
        dest="min_size",
        help="Only drill into entries larger than this (e.g. 500M, 1G). Default: 500M",
    )
    inspect_parser.add_argument(
        "--show-min",
        type=str,
        default="100M",
        dest="show_min",
        help="Hide entries smaller than this from display (e.g. 100M, 1G). Default: 100M",
    )

    sys_parser = sub.add_parser("system", help="Scan macOS system directories by category")
    sys_parser.add_argument(
        "--clean",
        action="store_true",
        help="Prompt to clean selected categories",
    )

    return parser


_SIZE_MULTIPLIERS = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}


def _parse_size(text: str) -> int:
    """Parse a human-readable size like '500M' or '1G' into bytes."""
    text = text.strip().upper()
    if text[-1] in _SIZE_MULTIPLIERS:
        return int(float(text[:-1]) * _SIZE_MULTIPLIERS[text[-1]])
    return int(text)


def _count_tree(entries: list) -> list:  # type: ignore[type-arg]
    """Flatten tree entries for counting."""
    result = []
    for e in entries:
        result.append(e)
        if e.children:
            result.extend(_count_tree(list(e.children)))
    return result


def _parse_selections(text: str, max_val: int) -> list[int]:
    """Parse comma-separated numbers like '1,3' into a sorted list of valid indices."""
    selected: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if part.isdigit():
            n = int(part)
            if 1 <= n <= max_val:
                selected.append(n)
    return sorted(set(selected))


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command in ("ls", "artifacts", "inspect"):
        target = Path(args.path).expanduser().resolve()
        if not target.is_dir():
            print(f"disk_free: not a directory: {target}", file=sys.stderr)
            sys.exit(1)

    if args.command == "ls":
        entries = scan_subdirs(target)
        print(format_table(entries))

    if args.command == "inspect":
        min_bytes = _parse_size(args.min_size)
        show_min_bytes = _parse_size(args.show_min)
        entries = deep_scan(
            target,
            depth=args.depth,
            min_bytes=min_bytes,
            on_scan=print_scan_progress,
        )
        finish_scan(sum(1 for _ in _count_tree(entries)))
        print(format_tree(entries, root=target, show_min_bytes=show_min_bytes))

    if args.command == "artifacts":
        artifacts = find_artifacts(target, on_scan=print_scan_progress)
        finish_scan(len(artifacts))
        print(format_artifacts_table(artifacts))

        if args.clean and artifacts:
            answer = input("\nRemove all artifacts? [y/N] ")
            if answer.strip().lower() == "y":
                result = clean_artifacts(
                    artifacts, on_remove=print_remove_progress,
                )
                finish_remove()
                print(f"Removed {result.removed} artifacts, freed {human_size(result.bytes_freed)}")
                if result.failed:
                    print(f"Failed to remove {result.failed} artifacts:")
                    for err in result.errors:
                        print(f"  {err}")
            else:
                print("Aborted.")

    if args.command == "system":
        results = scan_categories(
            DEFAULT_CATEGORIES, on_scan=print_system_scan_progress,
        )
        finish_system_scan()
        print(format_category_results(results))

        if args.clean and results:
            prompt = f"\nWhich categories to clean? [enter numbers 1-{len(results)}, e.g. 1,3]: "
            answer = input(prompt)
            selections = _parse_selections(answer, len(results))

            if not selections:
                print("Nothing selected.")
                return

            total_freed = 0
            total_removed = 0
            for idx in selections:
                cat_result = results[idx - 1]
                print(f"\nCleaning {cat_result.category.name}...")
                for i, entry in enumerate(cat_result.entries, 1):
                    print_dir_remove_progress(
                        i, len(cat_result.entries),
                        entry.size_bytes, entry.path,
                    )
                    try:
                        if entry.path.exists():
                            shutil.rmtree(entry.path)
                        total_freed += entry.size_bytes
                        total_removed += 1
                    except OSError as e:
                        finish_remove()
                        print(f"  Failed: {entry.path}: {e}")
                finish_remove()

            print(f"\nRemoved {total_removed} dirs, freed {human_size(total_freed)}")

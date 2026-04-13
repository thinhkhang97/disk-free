"""CLI entry point for disk_free."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .artifacts import Artifact, find_artifacts
from .formatter import format_tree, human_size
from .inspect import deep_scan
from .picker import PickerItem, run_picker
from .progress import (
    finish_remove,
    finish_scan,
    finish_system_scan,
    print_dir_remove_progress,
    print_scan_progress,
    print_system_scan_progress,
)
from .system import DEFAULT_CATEGORIES, scan_categories

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


def _artifacts_to_picker_items(
    artifacts: list[Artifact], root: Path,
) -> list[PickerItem]:
    """Convert artifacts to picker items with paths relative to root."""
    items: list[PickerItem] = []
    for a in artifacts:
        try:
            rel = a.path.relative_to(root)
        except ValueError:
            rel = a.path
        items.append(
            PickerItem(
                path=a.path,
                size_bytes=a.size_bytes,
                label=str(rel),
                description=a.rule_name,
                hint=a.regenerate_hint,
                group=a.rule_name,
            )
        )
    return items


def _remove_items(items: list[PickerItem]) -> None:
    """Remove selected picker items from disk with progress."""
    total_freed = 0
    total_removed = 0
    total_failed = 0

    for i, item in enumerate(items, 1):
        print_dir_remove_progress(i, len(items), item.size_bytes, item.path)
        try:
            if item.path.exists():
                shutil.rmtree(item.path)
            total_freed += item.size_bytes
            total_removed += 1
        except OSError as e:
            finish_remove()
            print(f"  Failed: {item.path}: {e}", file=sys.stderr)
            total_failed += 1

    finish_remove()
    print(f"Removed {total_removed} items, freed {human_size(total_freed)}")
    if total_failed:
        print(f"Failed to remove {total_failed} items")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="disk_free",
        description="Analyze disk usage and clean up safely.",
    )
    sub = parser.add_subparsers(dest="command")

    inspect_parser = sub.add_parser(
        "inspect",
        help="Inspect a directory — find removable build artifacts",
    )
    inspect_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    inspect_parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="How many levels deep to drill in overview (default: 3)",
    )
    inspect_parser.add_argument(
        "--min",
        type=str,
        default="500M",
        dest="min_size",
        help="Only drill into entries larger than this (default: 500M)",
    )
    inspect_parser.add_argument(
        "--show-min",
        type=str,
        default="100M",
        dest="show_min",
        help="Hide entries smaller than this in overview (default: 100M)",
    )

    sub.add_parser(
        "system",
        help="Scan macOS system directories for safe-to-remove caches",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "inspect":
        target = Path(args.path).expanduser().resolve()
        if not target.is_dir():
            print(f"disk_free: not a directory: {target}", file=sys.stderr)
            sys.exit(1)

        # Phase 1: overview tree
        min_bytes = _parse_size(args.min_size)
        show_min_bytes = _parse_size(args.show_min)
        tree = deep_scan(
            target, depth=args.depth, min_bytes=min_bytes,
            on_scan=print_scan_progress,
        )
        finish_scan(sum(1 for _ in _count_tree(tree)))
        print(format_tree(tree, root=target, show_min_bytes=show_min_bytes))

        # Phase 2: find removable artifacts
        print("\nScanning for removable artifacts...")
        artifacts = find_artifacts(target, on_scan=print_scan_progress)
        finish_scan(len(artifacts))

        if not artifacts:
            print("No removable artifacts found.")
            return

        total = sum(a.size_bytes for a in artifacts)
        print(f"Found {len(artifacts)} removable artifacts ({human_size(total)})\n")

        # Phase 3: interactive picker
        items = _artifacts_to_picker_items(artifacts, target)
        selected = run_picker(items)

        if selected is None or not selected:
            print("Nothing removed.")
            return

        _remove_items(selected)

    if args.command == "system":
        results = scan_categories(
            DEFAULT_CATEGORIES, on_scan=print_system_scan_progress,
        )
        finish_system_scan()

        if not results:
            print("No safe-to-remove items found.")
            return

        # Build picker items from system results
        items: list[PickerItem] = []
        target_lookup = {}
        for cat in DEFAULT_CATEGORIES:
            for t in cat.targets:
                target_lookup[str(t.path)] = (cat.name, t.description, t.regenerate_hint)

        for r in results:
            for entry in r.entries:
                group, desc, hint = target_lookup.get(
                    str(entry.path),
                    (r.category.name, entry.name, ""),
                )
                items.append(
                    PickerItem(
                        path=entry.path,
                        size_bytes=entry.size_bytes,
                        label=entry.name,
                        description=desc,
                        hint=hint,
                        group=group,
                    )
                )

        total = sum(item.size_bytes for item in items)
        print(f"Found {len(items)} safe-to-remove items ({human_size(total)})\n")

        selected = run_picker(items)

        if selected is None or not selected:
            print("Nothing removed.")
            return

        _remove_items(selected)

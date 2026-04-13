"""Format directory entries for display."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import Artifact
    from .inspect import TreeEntry
    from .scanner import DirEntry
    from .system import CategoryResult

_UNITS = ("B", "K", "M", "G", "T")


def human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string (e.g. '2.3G', '840M', '172K')."""
    if size_bytes == 0:
        return "0B"

    value = float(size_bytes)
    unit_index = 0
    while value >= 1024 and unit_index < len(_UNITS) - 1:
        value /= 1024
        unit_index += 1

    if value >= 100:
        formatted = f"{value:.0f}"
    elif value >= 10:
        formatted = f"{value:.1f}".rstrip("0").rstrip(".")
    else:
        formatted = f"{value:.1f}".rstrip("0").rstrip(".")

    return f"{formatted}{_UNITS[unit_index]}"


def format_table(entries: list[DirEntry]) -> str:
    """Format entries as a right-aligned size + name table."""
    if not entries:
        return "(empty)"

    lines: list[tuple[str, str]] = [
        (human_size(e.size_bytes), e.name) for e in entries
    ]
    max_size_width = max(len(size) for size, _ in lines)

    total_bytes = sum(e.size_bytes for e in entries)
    rows = [f"{size:>{max_size_width}}  {name}" for size, name in lines]
    rows.append(f"{'─' * max_size_width}  ──────")
    total_label = human_size(total_bytes)
    rows.append(f"{total_label:>{max_size_width}}  total ({len(entries)} dirs)")

    return "\n".join(rows)


def format_artifacts_table(artifacts: list[Artifact]) -> str:
    """Format artifact entries as a table with size, path, and regenerate hint."""
    if not artifacts:
        return "No removable artifacts found."

    lines: list[tuple[str, str, str]] = [
        (human_size(a.size_bytes), str(a.path), a.regenerate_hint)
        for a in artifacts
    ]
    max_size = max(len(s) for s, _, _ in lines)

    rows = [f"{size:>{max_size}}  {path}  ({hint})" for size, path, hint in lines]

    total_bytes = sum(a.size_bytes for a in artifacts)
    rows.append(f"{'─' * max_size}  ──────")
    total_label = human_size(total_bytes)
    rows.append(f"{total_label:>{max_size}}  removable ({len(artifacts)} artifacts)")

    return "\n".join(rows)


def format_category_results(results: list[CategoryResult]) -> str:
    """Format scan results grouped by category with numbered headers."""
    if not results:
        return "Nothing to show."

    sections: list[str] = []
    grand_total = 0

    for i, r in enumerate(results, 1):
        total = r.total_bytes
        grand_total += total

        # Build a lookup from path -> SafeTarget for hints
        target_by_path: dict[str, tuple[str, str]] = {}
        for t in r.category.targets:
            target_by_path[str(t.path)] = (t.description, t.regenerate_hint)

        header = f"[{i}] {r.category.name} ({human_size(total)}) — {r.category.description}"
        separator = "─" * len(header)

        lines: list[tuple[str, str, str]] = []
        for e in r.entries:
            desc, _hint = target_by_path.get(str(e.path), (e.name, ""))
            lines.append((human_size(e.size_bytes), e.name, desc))

        max_w = max(len(s) for s, _, _ in lines)

        rows = [header, separator]
        for size, name, desc in lines:
            rows.append(f"  {size:>{max_w}}  {name:<30}  {desc}")
        rows.append(f"  {'─' * max_w}  ──────")
        rows.append(f"  {human_size(total):>{max_w}}  total ({len(r.entries)} items)")

        sections.append("\n".join(rows))

    footer = f"\nGrand total: {human_size(grand_total)} across {len(results)} categories"
    sections.append(footer)

    return "\n\n".join(sections)


def format_tree(
    entries: list[TreeEntry],
    *,
    root: Path,
    show_min_bytes: int = 0,
) -> str:
    """Format a tree of entries with indentation for drilled children.

    *show_min_bytes* hides entries smaller than this from the display.
    Hidden entries are counted in an "and N more" line.
    """
    if not entries:
        return "(empty)"

    total_bytes = sum(e.size_bytes for e in entries)
    header = f"{root}  ({human_size(total_bytes)} total)"
    rows: list[str] = [header, "─" * len(header)]

    _format_tree_level(entries, rows, indent=0, show_min_bytes=show_min_bytes)

    return "\n".join(rows)


def _format_tree_level(
    entries: list[TreeEntry] | tuple[TreeEntry, ...],
    rows: list[str],
    indent: int,
    show_min_bytes: int,
) -> None:
    """Recursively format tree entries with increasing indentation."""
    if not entries:
        return

    visible = [e for e in entries if e.size_bytes >= show_min_bytes]
    hidden_count = len(entries) - len(visible)

    if not visible:
        return

    sizes = [human_size(e.size_bytes) for e in visible]
    max_w = max(len(s) for s in sizes)
    prefix = "  " * indent

    for entry, size_str in zip(visible, sizes):
        rows.append(f"{prefix}  {size_str:>{max_w}}  {entry.name}")
        if entry.children:
            _format_tree_level(entry.children, rows, indent + 1, show_min_bytes)

    if hidden_count > 0:
        hidden_bytes = sum(e.size_bytes for e in entries if e.size_bytes < show_min_bytes)
        rows.append(f"{prefix}  {'':>{max_w}}  ... and {hidden_count} more ({human_size(hidden_bytes)})")

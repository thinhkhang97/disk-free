"""Format directory entries for display."""

from __future__ import annotations

from .scanner import DirEntry

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

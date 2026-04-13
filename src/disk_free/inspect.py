"""Deep recursive scan that drills into large directories."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .scanner import dir_size

ScanCallback = Callable[[Path], None]


@dataclass(frozen=True)
class TreeEntry:
    """A directory entry that may have children if it was drilled into."""

    path: Path
    size_bytes: int
    children: tuple[TreeEntry, ...]

    @property
    def name(self) -> str:
        return self.path.name


def deep_scan(
    root: Path,
    *,
    depth: int = 2,
    min_bytes: int = 500_000_000,
    on_scan: ScanCallback | None = None,
) -> list[TreeEntry]:
    """Scan *root* and recursively drill into entries larger than *min_bytes*.

    Returns a tree of entries sorted largest-first at every level.
    *depth* controls how many levels deep to drill (1 = flat, no drill).
    """
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    return _scan_level(root, depth=depth, min_bytes=min_bytes, on_scan=on_scan)


def _scan_level(
    directory: Path,
    *,
    depth: int,
    min_bytes: int,
    on_scan: ScanCallback | None,
) -> list[TreeEntry]:
    """Scan one level of *directory*, drilling into large children."""
    try:
        children = sorted(directory.iterdir())
    except PermissionError:
        return []

    entries: list[TreeEntry] = []
    for child in children:
        if not child.is_dir():
            continue

        if on_scan is not None:
            on_scan(child)

        size = dir_size(child)

        sub_children: tuple[TreeEntry, ...] = ()
        if depth > 1 and size >= min_bytes:
            sub_children = tuple(
                _scan_level(
                    child,
                    depth=depth - 1,
                    min_bytes=min_bytes,
                    on_scan=on_scan,
                )
            )

        entries.append(TreeEntry(path=child, size_bytes=size, children=sub_children))

    entries.sort(key=lambda e: e.size_bytes, reverse=True)
    return entries

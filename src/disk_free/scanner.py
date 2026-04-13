"""Scan directories and compute their sizes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DirEntry:
    """A directory with its total size in bytes."""

    path: Path
    size_bytes: int

    @property
    def name(self) -> str:
        return self.path.name


def dir_size(path: Path) -> int:
    """Compute total size of a directory by walking all files.

    Does not follow symlinks to avoid loops.
    """
    total = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.lstat(fp).st_size
                except OSError:
                    pass
    except (PermissionError, OSError):
        pass
    return total


def scan_subdirs(root: Path) -> list[DirEntry]:
    """Scan immediate subdirectories of root and return their sizes, sorted largest first."""
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    entries: list[DirEntry] = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            entries.append(DirEntry(path=child, size_bytes=dir_size(child)))

    entries.sort(key=lambda e: e.size_bytes, reverse=True)
    return entries

"""Terminal progress display helpers."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artifacts import Artifact

from .formatter import human_size


def _term_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def _clear_line() -> None:
    sys.stderr.write(f"\r{' ' * _term_width()}\r")
    sys.stderr.flush()


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return "..." + text[-(max_len - 3):]


def _progress_bar(current: int, total: int, size_bytes: int, path: Path) -> str:
    """Build a progress bar string: [████░░░░] 3/10  1.2G  /path/..."""
    width = _term_width()
    pct = current / total
    bar_width = 20
    filled = int(bar_width * pct)
    bar = "█" * filled + "░" * (bar_width - filled)

    size = human_size(size_bytes)
    path_str = str(path)
    prefix = f"  [{bar}] {current}/{total}  {size:>5}  "
    max_path = width - len(prefix)
    return prefix + _truncate(path_str, max(max_path, 20))


# --- Artifact scanning ---


def print_scan_progress(directory: Path) -> None:
    """Overwrite the current line with the directory being scanned."""
    width = _term_width()
    label = f"Scanning: {_truncate(str(directory), width - 11)}"
    sys.stderr.write(f"\r{label:<{width}}")
    sys.stderr.flush()


def finish_scan(count: int) -> None:
    """Clear the scanning line and print a done message."""
    _clear_line()
    sys.stderr.write(f"Scan complete, found {count} artifacts.\n")
    sys.stderr.flush()


def print_remove_progress(current: int, total: int, artifact: Artifact) -> None:
    """Print a progress bar with the artifact being removed."""
    width = _term_width()
    line = _progress_bar(current, total, artifact.size_bytes, artifact.path)
    sys.stderr.write(f"\r{line:<{width}}")
    sys.stderr.flush()


def finish_remove() -> None:
    """Clear the progress line after removal is done."""
    _clear_line()


# --- System category scanning ---


def print_system_scan_progress(category_name: str, directory: Path) -> None:
    """Overwrite the current line with category + directory being scanned."""
    width = _term_width()
    dir_str = _truncate(str(directory), width - len(category_name) - 15)
    label = f"Scanning [{category_name}]: {dir_str}"
    sys.stderr.write(f"\r{label:<{width}}")
    sys.stderr.flush()


def finish_system_scan() -> None:
    """Clear the system scanning line."""
    _clear_line()


def print_dir_remove_progress(current: int, total: int, size_bytes: int, path: Path) -> None:
    """Print a progress bar for removing a directory entry."""
    width = _term_width()
    line = _progress_bar(current, total, size_bytes, path)
    sys.stderr.write(f"\r{line:<{width}}")
    sys.stderr.flush()

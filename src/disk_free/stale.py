"""Discover large, untouched files by walking a directory tree.

The ``system`` and ``inspect`` commands work from curated allowlists (known
cache paths, known artifact directory names). This module is the third mode:
heuristic discovery of files the user probably forgot about — ranked by
``size_bytes * age_days``.

Key design choices:

- **Files only**, never directories. A directory's mtime shifts whenever any
  child is touched, so it is a poor signal for "untouched." Files are also
  what actually consume bytes.
- **mtime, not atime.** macOS/APFS updates atime but Spotlight indexing,
  Time Machine, and even ``ls`` nudge it. We still record atime on the
  ``StaleFile`` for display, but ranking uses mtime.
- **Hard exclusion list.** Heuristic discovery will otherwise surface
  ``~/Documents/taxes.pdf`` next to ``~/Downloads/installer.dmg``. The
  walker skips a fixed set of dotfile dirs (``.git``, ``node_modules``,
  ``.venv`` …) and, when scanning inside ``$HOME``, a fixed set of
  user-data subtrees (``Documents``, ``Desktop``, iCloud, Photos Library …).
  Everything surfaced by this module should be flagged ``safety="caution"``
  at the CLI layer.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ScanCallback = Callable[[Path], None]

# Directory names we never descend into, regardless of where they appear.
# These are either known artifact dirs (handled by `inspect`) or VCS/system
# dirs that shouldn't surface as "stale files" to delete.
EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
        # Version control
        ".git",
        ".hg",
        ".svn",
        # Node / JS
        "node_modules",
        # Python
        ".venv",
        "venv",
        "__pycache__",
        # Build outputs — covered by `inspect`, not interesting here
        ".next",
        "dist",
        "build",
        "target",
        ".gradle",
        ".turbo",
        ".expo",
        # macOS bundles — internal structure shouldn't be picked over
        # (matches by name for *.app/*.framework directories themselves)
    }
)

# Paths under $HOME we never descend into by default. These contain user
# data (photos, documents, mail, iCloud) where a stale-file recommendation
# would be catastrophic if followed.
_HOME_RELATIVE_EXCLUDES: tuple[str, ...] = (
    "Documents",
    "Desktop",
    "Pictures",
    "Movies",
    "Music",
    "Library/Mobile Documents",  # iCloud Drive
    "Library/Mail",
    "Library/Messages",
    "Library/Containers/com.apple.mail",
    "Library/Application Support/AddressBook",
    "Library/Application Support/MobileSync",  # iOS backups (worth keeping)
)


def default_excluded_paths(home: Path | None = None) -> tuple[Path, ...]:
    """Return the default set of absolute paths to skip.

    These are the sensitive user-data dirs under $HOME. Pass ``home``
    for tests; defaults to :py:meth:`Path.home`.
    """
    base = home if home is not None else Path.home()
    return tuple(base / p for p in _HOME_RELATIVE_EXCLUDES)


@dataclass(frozen=True)
class StaleFile:
    """A file flagged as "large and old."

    *score* is ``size_bytes * age_days``; higher score = stronger recommendation.
    *reason* is a human-readable explanation ready for display.
    """

    path: Path
    size_bytes: int
    mtime: float
    atime: float
    age_days: int
    score: float
    reason: str


def find_stale_files(
    root: Path,
    *,
    min_size_bytes: int = 10 * 1024 * 1024,
    min_age_days: int = 90,
    top_n: int = 30,
    excluded_dir_names: frozenset[str] = EXCLUDED_DIR_NAMES,
    excluded_paths: tuple[Path, ...] = (),
    now: float | None = None,
    on_scan: ScanCallback | None = None,
) -> list[StaleFile]:
    """Walk *root* and return up to *top_n* stale files, ranked by score.

    A file is "stale" when it is at least *min_size_bytes* and has not been
    modified in at least *min_age_days*. Ranking is ``size_bytes * age_days``
    (both clipped at 1 to keep the product meaningful at the boundary).

    The walk skips:
    - symlinks (to avoid loops like Steam.app's self-referential bundle)
    - directory names in *excluded_dir_names*
    - directories whose resolved path appears in *excluded_paths*
    - files/dirs that raise ``PermissionError``/``OSError`` on stat

    *now* lets tests pin the current time; defaults to ``time.time()``.
    """
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    current_time = now if now is not None else time.time()
    # Normalise exclusion paths to absolute for comparison.
    excluded_abs = frozenset(p.resolve() for p in excluded_paths)

    collected: list[StaleFile] = []
    _walk(
        root,
        collected=collected,
        min_size_bytes=min_size_bytes,
        min_age_days=min_age_days,
        excluded_dir_names=excluded_dir_names,
        excluded_abs=excluded_abs,
        now=current_time,
        on_scan=on_scan,
    )

    collected.sort(key=lambda f: f.score, reverse=True)
    return collected[:top_n]


def _walk(
    directory: Path,
    *,
    collected: list[StaleFile],
    min_size_bytes: int,
    min_age_days: int,
    excluded_dir_names: frozenset[str],
    excluded_abs: frozenset[Path],
    now: float,
    on_scan: ScanCallback | None,
) -> None:
    """Recursively collect stale files under *directory*."""
    if on_scan is not None:
        on_scan(directory)

    try:
        children = list(os.scandir(directory))
    except (PermissionError, OSError):
        return

    for child in children:
        try:
            if child.is_symlink():
                continue
            if child.is_dir(follow_symlinks=False):
                if child.name in excluded_dir_names:
                    continue
                child_path = Path(child.path)
                try:
                    resolved = child_path.resolve()
                except OSError:
                    resolved = child_path
                if resolved in excluded_abs:
                    continue
                _walk(
                    child_path,
                    collected=collected,
                    min_size_bytes=min_size_bytes,
                    min_age_days=min_age_days,
                    excluded_dir_names=excluded_dir_names,
                    excluded_abs=excluded_abs,
                    now=now,
                    on_scan=on_scan,
                )
                continue

            if not child.is_file(follow_symlinks=False):
                continue

            stat = child.stat(follow_symlinks=False)
        except (PermissionError, OSError):
            continue

        size = stat.st_size
        if size < min_size_bytes:
            continue

        age_seconds = now - stat.st_mtime
        age_days = int(age_seconds // 86_400)
        if age_days < min_age_days:
            continue

        score = float(max(size, 1)) * float(max(age_days, 1))
        collected.append(
            StaleFile(
                path=Path(child.path),
                size_bytes=size,
                mtime=stat.st_mtime,
                atime=stat.st_atime,
                age_days=age_days,
                score=score,
                reason=_build_reason(age_days),
            )
        )


def _build_reason(age_days: int) -> str:
    """Human-readable freshness label: 'untouched 14 months', 'untouched 3 weeks'."""
    if age_days >= 365:
        years = age_days / 365
        if years >= 2:
            return f"untouched {years:.1f} years"
        return f"untouched {int(age_days / 30)} months"
    if age_days >= 60:
        return f"untouched {int(age_days / 30)} months"
    if age_days >= 14:
        return f"untouched {int(age_days / 7)} weeks"
    return f"untouched {age_days} days"

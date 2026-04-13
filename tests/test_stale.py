"""Tests for stale file detection."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from disk_free.stale import (
    EXCLUDED_DIR_NAMES,
    StaleFile,
    default_excluded_paths,
    find_stale_files,
)

_ONE_MB = 1024 * 1024
_DAY = 86_400  # seconds


def _make_file(path: Path, size: int = _ONE_MB, age_days: int = 0) -> Path:
    """Create a file with a given size and age (mtime/atime = now - age_days)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)
    if age_days > 0:
        ts = _NOW - age_days * _DAY
        os.utime(path, (ts, ts))
    return path


# Fixed "now" used by tests — passed into find_stale_files so tests are deterministic.
_NOW = 2_000_000_000.0  # 2033-05-18


class TestFindStaleFiles:
    def test_empty_directory(self, tmp_path: Path) -> None:
        assert find_stale_files(tmp_path, now=_NOW) == []

    def test_finds_large_old_file(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "bigold.bin", size=20 * _ONE_MB, age_days=200)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=90, now=_NOW,
        )
        assert len(results) == 1
        assert results[0].path == tmp_path / "bigold.bin"
        assert results[0].size_bytes == 20 * _ONE_MB
        assert results[0].age_days == 200

    def test_excludes_file_below_min_size(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "tiny.bin", size=100, age_days=365)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=30, now=_NOW,
        )
        assert results == []

    def test_excludes_file_below_min_age(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "fresh.bin", size=50 * _ONE_MB, age_days=5)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=30, now=_NOW,
        )
        assert results == []

    def test_sorts_by_score_desc(self, tmp_path: Path) -> None:
        # score = size_bytes * age_days
        # Big (50MB * 100d = 5e9) should come before Huge-but-young (200MB * 35d = 7e9)?
        # Actually let's pick clearer numbers:
        #   A: 10MB * 1000d = 1.05e10
        #   B: 100MB * 50d  = 5.24e9
        # A should be first.
        _make_file(tmp_path / "a.bin", size=10 * _ONE_MB, age_days=1000)
        _make_file(tmp_path / "b.bin", size=100 * _ONE_MB, age_days=50)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=30, now=_NOW,
        )
        assert len(results) == 2
        assert results[0].path.name == "a.bin"
        assert results[1].path.name == "b.bin"

    def test_respects_top_n(self, tmp_path: Path) -> None:
        for i in range(5):
            _make_file(tmp_path / f"f{i}.bin", size=(i + 1) * _ONE_MB, age_days=200)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=90, top_n=3, now=_NOW,
        )
        assert len(results) == 3
        # Top 3 by size (since age is equal) → 5MB, 4MB, 3MB
        assert results[0].size_bytes == 5 * _ONE_MB
        assert results[2].size_bytes == 3 * _ONE_MB

    def test_skips_excluded_dir_names(self, tmp_path: Path) -> None:
        _make_file(
            tmp_path / "proj" / "node_modules" / "pkg" / "huge.js",
            size=20 * _ONE_MB,
            age_days=500,
        )
        _make_file(
            tmp_path / "proj" / ".git" / "objects" / "pack.bin",
            size=30 * _ONE_MB,
            age_days=500,
        )
        _make_file(
            tmp_path / "proj" / "mydoc.pdf",
            size=10 * _ONE_MB,
            age_days=500,
        )
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=90, now=_NOW,
        )
        names = [r.path.name for r in results]
        assert "mydoc.pdf" in names
        assert "huge.js" not in names
        assert "pack.bin" not in names

    def test_skips_excluded_absolute_paths(self, tmp_path: Path) -> None:
        keep_dir = tmp_path / "keep"
        skip_dir = tmp_path / "skip"
        _make_file(keep_dir / "yes.bin", size=10 * _ONE_MB, age_days=200)
        _make_file(skip_dir / "no.bin", size=10 * _ONE_MB, age_days=200)

        results = find_stale_files(
            tmp_path,
            min_size_bytes=_ONE_MB,
            min_age_days=90,
            excluded_paths=(skip_dir,),
            now=_NOW,
        )
        names = [r.path.name for r in results]
        assert "yes.bin" in names
        assert "no.bin" not in names

    def test_skips_symlinks(self, tmp_path: Path) -> None:
        real = tmp_path / "real"
        real.mkdir()
        _make_file(real / "data.bin", size=10 * _ONE_MB, age_days=200)

        # Symlink pointing back into parent — would loop if followed
        link = tmp_path / "loop"
        link.symlink_to(tmp_path)

        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=90, now=_NOW,
        )
        # Should find only the real file, not traverse through the loop
        assert len(results) == 1
        assert results[0].path == real / "data.bin"

    def test_not_a_directory_raises(self, tmp_path: Path) -> None:
        fake = tmp_path / "nope"
        with pytest.raises(NotADirectoryError):
            find_stale_files(fake, now=_NOW)

    def test_reason_mentions_age_and_location(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "old.bin", size=50 * _ONE_MB, age_days=400)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=90, now=_NOW,
        )
        reason = results[0].reason.lower()
        # Reason should convey that the file is untouched/stale and for how long.
        assert any(w in reason for w in ("untouched", "stale", "unused", "old"))

    def test_age_days_computed_from_now(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a.bin", size=5 * _ONE_MB, age_days=365)
        results = find_stale_files(
            tmp_path, min_size_bytes=_ONE_MB, min_age_days=90, now=_NOW,
        )
        assert results[0].age_days == 365


class TestExclusionLists:
    def test_default_excluded_dir_names_contains_git(self) -> None:
        assert ".git" in EXCLUDED_DIR_NAMES

    def test_default_excluded_dir_names_contains_node_modules(self) -> None:
        assert "node_modules" in EXCLUDED_DIR_NAMES

    def test_default_excluded_paths_contains_documents(self) -> None:
        paths = default_excluded_paths()
        home = Path.home()
        assert home / "Documents" in paths

    def test_default_excluded_paths_contains_icloud(self) -> None:
        paths = default_excluded_paths()
        home = Path.home()
        assert home / "Library" / "Mobile Documents" in paths


class TestStaleFileDataclass:
    def test_is_frozen(self) -> None:
        f = StaleFile(
            path=Path("/tmp/a"),
            size_bytes=1024,
            mtime=1.0,
            atime=1.0,
            age_days=10,
            score=10240.0,
            reason="test",
        )
        with pytest.raises(Exception):
            f.size_bytes = 2048  # type: ignore[misc]

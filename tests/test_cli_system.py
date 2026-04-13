"""Tests for CLI system command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from disk_free.cli import main
from disk_free.system import Category, SafeTarget


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


def _test_categories(tmp_path: Path) -> list[Category]:
    """Create test categories with targets pointing at tmp_path subdirs."""
    return [
        Category(
            name="Caches",
            description="caches",
            targets=(
                SafeTarget(tmp_path / "Caches" / "Google", "Chrome cache", "rebuild"),
            ),
        ),
        Category(
            name="Developer",
            description="dev",
            targets=(
                SafeTarget(tmp_path / "Developer" / "DerivedData", "Xcode build", "rebuild"),
            ),
        ),
    ]


class TestSystemCommand:
    def test_shows_categories(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        _make_file(tmp_path / "Caches" / "Google" / "data.bin", size=5000)
        _make_file(tmp_path / "Developer" / "DerivedData" / "build.o", size=3000)

        cats = _test_categories(tmp_path)
        with patch("disk_free.cli.DEFAULT_CATEGORIES", cats):
            main(["system"])

        out = capsys.readouterr().out
        assert "Caches" in out
        assert "Developer" in out

    def test_clean_prompts_per_category(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        _make_file(tmp_path / "Caches" / "Google" / "data.bin", size=5000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("builtins.input", return_value=""),
        ):
            main(["system", "--clean"])

        out = capsys.readouterr().out
        assert "Caches" in out

    def test_clean_removes_selected_category(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        google = tmp_path / "Caches" / "Google"
        _make_file(google / "data.bin", size=5000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("builtins.input", return_value="1"),
        ):
            main(["system", "--clean"])

        assert not google.exists()
        out = capsys.readouterr().out
        assert "Removed" in out

    def test_clean_skips_on_empty_input(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        google = tmp_path / "Caches" / "Google"
        _make_file(google / "data.bin", size=5000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("builtins.input", return_value=""),
        ):
            main(["system", "--clean"])

        assert google.exists()

    def test_clean_multiple_categories(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        google = tmp_path / "Caches" / "Google"
        derived = tmp_path / "Developer" / "DerivedData"
        _make_file(google / "data.bin", size=5000)
        _make_file(derived / "build.o", size=3000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("builtins.input", return_value="1,2"),
        ):
            main(["system", "--clean"])

        assert not google.exists()
        assert not derived.exists()

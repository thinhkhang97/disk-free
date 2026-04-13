"""Tests for CLI system command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from disk_free.cli import main
from disk_free.picker import PickerItem
from disk_free.system import Category, SafeTarget


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


def _test_categories(tmp_path: Path) -> list[Category]:
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
    def test_shows_items_and_picker(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        _make_file(tmp_path / "Caches" / "Google" / "data.bin", size=5000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("disk_free.cli.run_picker", return_value=[]),
        ):
            main(["system"])

        out = capsys.readouterr().out
        assert "safe-to-remove" in out

    def test_picker_called_with_system_items(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "Caches" / "Google" / "data.bin", size=5000)
        _make_file(tmp_path / "Developer" / "DerivedData" / "build.o", size=3000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("disk_free.cli.run_picker", return_value=[]) as mock,
        ):
            main(["system"])

        mock.assert_called_once()
        items = mock.call_args[0][0]
        assert len(items) == 2
        groups = {item.group for item in items}
        assert "Caches" in groups
        assert "Developer" in groups

    def test_removes_selected(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        google = tmp_path / "Caches" / "Google"
        _make_file(google / "data.bin", size=5000)

        cats = _test_categories(tmp_path)
        selected = [
            PickerItem(
                path=google, size_bytes=5000, label="Google",
                description="Chrome cache", hint="rebuild", group="Caches",
            )
        ]
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("disk_free.cli.run_picker", return_value=selected),
        ):
            main(["system"])

        assert not google.exists()
        out = capsys.readouterr().out
        assert "Removed" in out

    def test_no_items_found(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        cats = _test_categories(tmp_path)
        with patch("disk_free.cli.DEFAULT_CATEGORIES", cats):
            main(["system"])

        out = capsys.readouterr().out
        assert "No safe-to-remove" in out

    def test_picker_cancelled(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        google = tmp_path / "Caches" / "Google"
        _make_file(google / "data.bin", size=5000)

        cats = _test_categories(tmp_path)
        with (
            patch("disk_free.cli.DEFAULT_CATEGORIES", cats),
            patch("disk_free.cli.run_picker", return_value=None),
        ):
            main(["system"])

        assert google.exists()
        out = capsys.readouterr().out
        assert "Nothing removed" in out

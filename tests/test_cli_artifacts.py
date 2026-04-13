"""Tests for CLI inspect command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from disk_free.cli import main


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


class TestInspectCommand:
    def test_shows_tree_and_artifacts(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        _make_file(tmp_path / "app" / "node_modules" / "x.js", size=5000)
        _make_file(tmp_path / "app" / "src" / "main.js", size=100)

        with patch("disk_free.cli.run_picker", return_value=[]):
            main(["inspect", str(tmp_path), "--show-min", "0"])

        out = capsys.readouterr().out
        assert "app" in out
        assert "removable artifact" in out

    def test_picker_called_with_artifacts(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "proj" / "node_modules" / "x.js", size=5000)

        with patch("disk_free.cli.run_picker", return_value=[]) as mock:
            main(["inspect", str(tmp_path)])

        mock.assert_called_once()
        items = mock.call_args[0][0]
        assert len(items) == 1
        assert "node_modules" in items[0].label

    def test_no_artifacts_found(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        _make_file(tmp_path / "src" / "main.py", size=100)

        main(["inspect", str(tmp_path)])

        out = capsys.readouterr().out
        assert "No removable artifacts" in out

    def test_removes_selected_items(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "x.js", size=5000)

        from disk_free.picker import PickerItem

        selected = [
            PickerItem(
                path=nm, size_bytes=5000, label="node_modules",
                description="npm", hint="npm install", group="node_modules",
            )
        ]

        with patch("disk_free.cli.run_picker", return_value=selected):
            main(["inspect", str(tmp_path)])

        assert not nm.exists()
        out = capsys.readouterr().out
        assert "Removed" in out

    def test_picker_cancelled(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "x.js", size=5000)

        with patch("disk_free.cli.run_picker", return_value=None):
            main(["inspect", str(tmp_path)])

        assert nm.exists()
        out = capsys.readouterr().out
        assert "Nothing removed" in out

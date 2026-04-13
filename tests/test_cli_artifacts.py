"""Tests for CLI artifacts command with --clean flag."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from disk_free.cli import main


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


class TestArtifactsCleanFlag:
    def test_clean_flag_prompts_and_removes(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "x.js")

        with patch("builtins.input", return_value="y"):
            main(["artifacts", str(tmp_path), "--clean"])

        assert not nm.exists()
        out = capsys.readouterr().out
        assert "Removed" in out

    def test_clean_flag_aborts_on_no(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "x.js")

        with patch("builtins.input", return_value="n"):
            main(["artifacts", str(tmp_path), "--clean"])

        assert nm.exists()
        out = capsys.readouterr().out
        assert "Aborted" in out

    def test_clean_flag_empty_input_aborts(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "x.js")

        with patch("builtins.input", return_value=""):
            main(["artifacts", str(tmp_path), "--clean"])

        assert nm.exists()

    def test_no_clean_flag_does_not_prompt(self, tmp_path: Path) -> None:
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "x.js")

        with patch("builtins.input") as mock_input:
            main(["artifacts", str(tmp_path)])

        mock_input.assert_not_called()
        assert nm.exists()

    def test_no_artifacts_skips_prompt(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        with patch("builtins.input") as mock_input:
            main(["artifacts", str(tmp_path), "--clean"])

        mock_input.assert_not_called()

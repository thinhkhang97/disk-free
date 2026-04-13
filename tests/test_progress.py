"""Tests for progress callbacks in find_artifacts and clean_artifacts."""

from __future__ import annotations

from pathlib import Path

from disk_free.artifacts import Artifact, clean_artifacts, find_artifacts


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


def _artifact(path: Path, size: int = 1024) -> Artifact:
    return Artifact(
        path=path,
        size_bytes=size,
        rule_name=path.name,
        regenerate_hint="regenerate",
    )


class TestFindArtifactsProgress:
    def test_callback_called_for_each_scanned_dir(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "node_modules" / "x.js")
        _make_file(tmp_path / "b" / "src" / "y.py")

        scanned: list[Path] = []
        find_artifacts(tmp_path, on_scan=lambda p: scanned.append(p))

        # Should have been called for at least: a, b, b/src
        assert len(scanned) >= 3
        assert all(isinstance(p, Path) for p in scanned)

    def test_callback_not_required(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "node_modules" / "x.js")
        results = find_artifacts(tmp_path)
        assert len(results) == 1

    def test_callback_receives_child_dirs_not_files(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "project" / "src" / "main.py")

        scanned: list[Path] = []
        find_artifacts(tmp_path, on_scan=lambda p: scanned.append(p))

        for p in scanned:
            assert p.is_dir()


class TestCleanArtifactsProgress:
    def test_callback_called_for_each_artifact(self, tmp_path: Path) -> None:
        nm = tmp_path / "a" / "node_modules"
        nxt = tmp_path / "b" / ".next"
        _make_file(nm / "x.js")
        _make_file(nxt / "y.js")

        progress: list[tuple[int, int, Artifact]] = []
        clean_artifacts(
            [_artifact(nm), _artifact(nxt)],
            on_remove=lambda cur, total, a: progress.append((cur, total, a)),
        )

        assert len(progress) == 2
        assert progress[0] == (1, 2, _artifact(nm))
        assert progress[1] == (2, 2, _artifact(nxt))

    def test_callback_not_required(self, tmp_path: Path) -> None:
        nm = tmp_path / "a" / "node_modules"
        _make_file(nm / "x.js")
        result = clean_artifacts([_artifact(nm)])
        assert result.removed == 1

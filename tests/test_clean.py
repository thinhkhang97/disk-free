"""Tests for artifact cleaning."""

from __future__ import annotations

from pathlib import Path

from disk_free.artifacts import Artifact, clean_artifacts, CleanResult


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


class TestCleanArtifacts:
    def test_removes_single_artifact(self, tmp_path: Path) -> None:
        nm = tmp_path / "app" / "node_modules"
        _make_file(nm / "pkg" / "index.js")
        assert nm.exists()

        result = clean_artifacts([_artifact(nm)])

        assert not nm.exists()
        assert result.removed == 1
        assert result.failed == 0
        assert result.bytes_freed > 0

    def test_removes_multiple_artifacts(self, tmp_path: Path) -> None:
        nm = tmp_path / "a" / "node_modules"
        nxt = tmp_path / "b" / ".next"
        _make_file(nm / "x.js", size=2000)
        _make_file(nxt / "cache" / "y.json", size=3000)

        result = clean_artifacts([_artifact(nm, 2000), _artifact(nxt, 3000)])

        assert not nm.exists()
        assert not nxt.exists()
        assert result.removed == 2
        assert result.bytes_freed == 5000

    def test_handles_already_missing_dir(self, tmp_path: Path) -> None:
        gone = tmp_path / "gone" / "node_modules"
        result = clean_artifacts([_artifact(gone)])

        assert result.removed == 1
        assert result.failed == 0

    def test_handles_permission_error(self, tmp_path: Path) -> None:
        locked = tmp_path / "locked" / "node_modules"
        _make_file(locked / "x.js")
        locked.chmod(0o000)

        result = clean_artifacts([_artifact(locked)])

        assert result.failed == 1
        assert len(result.errors) == 1
        # restore permissions for cleanup
        locked.chmod(0o755)

    def test_empty_list(self) -> None:
        result = clean_artifacts([])
        assert result.removed == 0
        assert result.failed == 0
        assert result.bytes_freed == 0

    def test_parent_directory_preserved(self, tmp_path: Path) -> None:
        parent = tmp_path / "my-app"
        nm = parent / "node_modules"
        _make_file(nm / "pkg" / "index.js")
        _make_file(parent / "package.json", size=100)

        clean_artifacts([_artifact(nm)])

        assert parent.exists()
        assert (parent / "package.json").exists()
        assert not nm.exists()


class TestCleanResult:
    def test_fields(self) -> None:
        r = CleanResult(removed=3, failed=1, bytes_freed=5000, errors=["oops"])
        assert r.removed == 3
        assert r.failed == 1
        assert r.bytes_freed == 5000
        assert r.errors == ["oops"]

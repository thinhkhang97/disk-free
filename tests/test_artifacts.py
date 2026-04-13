"""Tests for artifact detection."""

from __future__ import annotations

from pathlib import Path

from disk_free.artifacts import Artifact, find_artifacts, ARTIFACT_RULES


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


class TestArtifactRules:
    def test_node_modules_is_a_rule(self) -> None:
        names = {r.dir_name for r in ARTIFACT_RULES}
        assert "node_modules" in names

    def test_next_is_a_rule(self) -> None:
        names = {r.dir_name for r in ARTIFACT_RULES}
        assert ".next" in names

    def test_venv_is_a_rule(self) -> None:
        names = {r.dir_name for r in ARTIFACT_RULES}
        assert ".venv" in names

    def test_pycache_is_a_rule(self) -> None:
        names = {r.dir_name for r in ARTIFACT_RULES}
        assert "__pycache__" in names


class TestFindArtifacts:
    def test_empty_directory(self, tmp_path: Path) -> None:
        assert find_artifacts(tmp_path) == []

    def test_finds_node_modules(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "my-app" / "node_modules" / "lodash" / "index.js")
        results = find_artifacts(tmp_path)
        assert len(results) == 1
        assert results[0].path == tmp_path / "my-app" / "node_modules"
        assert results[0].size_bytes > 0

    def test_finds_dot_next(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "web" / ".next" / "cache" / "data.json", size=2048)
        results = find_artifacts(tmp_path)
        assert len(results) == 1
        assert results[0].path.name == ".next"

    def test_finds_venv(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "project" / ".venv" / "lib" / "site.py")
        results = find_artifacts(tmp_path)
        assert len(results) == 1
        assert results[0].path.name == ".venv"

    def test_finds_pycache(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "src" / "__pycache__" / "mod.cpython-313.pyc")
        results = find_artifacts(tmp_path)
        assert len(results) == 1
        assert results[0].path.name == "__pycache__"

    def test_does_not_descend_into_artifacts(self, tmp_path: Path) -> None:
        """node_modules inside another node_modules should not be reported separately."""
        _make_file(
            tmp_path / "app" / "node_modules" / "pkg" / "node_modules" / "dep" / "i.js"
        )
        results = find_artifacts(tmp_path)
        assert len(results) == 1
        assert results[0].path == tmp_path / "app" / "node_modules"

    def test_multiple_projects(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "node_modules" / "x.js", size=3000)
        _make_file(tmp_path / "b" / ".next" / "y.js", size=1000)
        _make_file(tmp_path / "c" / ".venv" / "z.py", size=2000)
        results = find_artifacts(tmp_path)
        assert len(results) == 3

    def test_sorted_largest_first(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "small" / "node_modules" / "x.js", size=100)
        _make_file(tmp_path / "large" / "node_modules" / "y.js", size=5000)
        results = find_artifacts(tmp_path)
        assert results[0].size_bytes >= results[1].size_bytes

    def test_not_a_directory_raises(self, tmp_path: Path) -> None:
        import pytest

        fake = tmp_path / "not-real"
        with pytest.raises(NotADirectoryError):
            find_artifacts(fake)

    def test_skips_hidden_git_dir(self, tmp_path: Path) -> None:
        """The .git directory itself should not be reported as an artifact."""
        _make_file(tmp_path / "repo" / ".git" / "objects" / "abc")
        results = find_artifacts(tmp_path)
        assert len(results) == 0


class TestArtifactDataclass:
    def test_artifact_fields(self) -> None:
        a = Artifact(
            path=Path("/app/node_modules"),
            size_bytes=1_000_000,
            rule_name="node_modules",
            regenerate_hint="npm install",
        )
        assert a.path == Path("/app/node_modules")
        assert a.size_bytes == 1_000_000
        assert a.rule_name == "node_modules"
        assert a.regenerate_hint == "npm install"

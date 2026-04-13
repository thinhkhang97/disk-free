"""Tests for deep inspect scanning."""

from __future__ import annotations

from pathlib import Path

from disk_free.inspect import TreeEntry, deep_scan


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


class TestTreeEntry:
    def test_fields(self) -> None:
        e = TreeEntry(path=Path("/a/b"), size_bytes=1000, children=())
        assert e.name == "b"
        assert e.size_bytes == 1000
        assert e.children == ()

    def test_with_children(self) -> None:
        child = TreeEntry(path=Path("/a/b/c"), size_bytes=500, children=())
        parent = TreeEntry(path=Path("/a/b"), size_bytes=1000, children=(child,))
        assert len(parent.children) == 1
        assert parent.children[0].name == "c"


class TestDeepScan:
    def test_flat_scan(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "x.bin", size=5000)
        _make_file(tmp_path / "b" / "y.bin", size=3000)

        entries = deep_scan(tmp_path, depth=1, min_bytes=0)
        assert len(entries) == 2
        assert entries[0].size_bytes >= entries[1].size_bytes
        assert entries[0].children == ()

    def test_drills_into_large_entries(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "big" / "sub1" / "x.bin", size=5000)
        _make_file(tmp_path / "big" / "sub2" / "y.bin", size=3000)
        _make_file(tmp_path / "small" / "z.bin", size=100)

        entries = deep_scan(tmp_path, depth=2, min_bytes=1000)

        big = next(e for e in entries if e.name == "big")
        small = next(e for e in entries if e.name == "small")

        # big should have children drilled
        assert len(big.children) >= 2
        # small is below threshold, no drill
        assert small.children == ()

    def test_respects_max_depth(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "b" / "c" / "d" / "x.bin", size=5000)

        entries = deep_scan(tmp_path, depth=2, min_bytes=0)
        # depth=2: root -> a -> b (stop, no further drill into c)
        a = entries[0]
        assert len(a.children) >= 1
        b = a.children[0]
        assert b.children == ()  # stopped at depth 2

    def test_depth_3(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "b" / "c" / "x.bin", size=5000)

        entries = deep_scan(tmp_path, depth=3, min_bytes=0)
        a = entries[0]
        b = a.children[0]
        assert len(b.children) >= 1  # drilled into level 3

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert deep_scan(tmp_path, depth=2, min_bytes=0) == []

    def test_not_a_directory_raises(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(NotADirectoryError):
            deep_scan(tmp_path / "nope", depth=2, min_bytes=0)

    def test_sorted_largest_first_at_each_level(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "big" / "large" / "x.bin", size=5000)
        _make_file(tmp_path / "big" / "small" / "y.bin", size=100)

        entries = deep_scan(tmp_path, depth=2, min_bytes=0)
        big = entries[0]
        assert big.children[0].size_bytes >= big.children[1].size_bytes

    def test_skips_permission_errors(self, tmp_path: Path) -> None:
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0o000)

        ok = tmp_path / "ok"
        _make_file(ok / "x.bin", size=1000)

        entries = deep_scan(tmp_path, depth=1, min_bytes=0)
        names = [e.name for e in entries]
        assert "ok" in names
        # locked dir reports 0 bytes, may or may not appear
        locked.chmod(0o755)

    def test_on_scan_callback(self, tmp_path: Path) -> None:
        _make_file(tmp_path / "a" / "x.bin", size=1000)

        scanned: list[Path] = []
        deep_scan(tmp_path, depth=1, min_bytes=0, on_scan=lambda p: scanned.append(p))
        assert len(scanned) >= 1

    def test_skips_symlink_loops(self, tmp_path: Path) -> None:
        """Self-referential symlinks must not cause infinite recursion."""
        app = tmp_path / "App"
        app.mkdir()
        (app / "self").symlink_to(app)
        _make_file(app / "sub" / "x.bin", size=1000)

        entries = deep_scan(tmp_path, depth=5, min_bytes=0)
        # Should complete without hanging
        assert len(entries) == 1

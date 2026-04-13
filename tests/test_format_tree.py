"""Tests for tree formatting."""

from __future__ import annotations

from pathlib import Path

from disk_free.formatter import format_tree
from disk_free.inspect import TreeEntry


class TestFormatTree:
    def test_flat_entries(self) -> None:
        entries = [
            TreeEntry(path=Path("/lib/Google"), size_bytes=7_000_000_000, children=()),
            TreeEntry(path=Path("/lib/pip"), size_bytes=1_000_000_000, children=()),
        ]
        out = format_tree(entries, root=Path("/lib"))
        assert "Google" in out
        assert "pip" in out
        assert "/lib" in out

    def test_nested_entries(self) -> None:
        child = TreeEntry(path=Path("/lib/App/Steam"), size_bytes=24_000_000_000, children=())
        parent = TreeEntry(path=Path("/lib/App"), size_bytes=73_000_000_000, children=(child,))
        out = format_tree([parent], root=Path("/lib"))
        assert "App" in out
        assert "Steam" in out

    def test_indentation_increases_with_depth(self) -> None:
        grandchild = TreeEntry(path=Path("/a/b/c"), size_bytes=100, children=())
        child = TreeEntry(path=Path("/a/b"), size_bytes=200, children=(grandchild,))
        parent = TreeEntry(path=Path("/a"), size_bytes=300, children=(child,))

        out = format_tree([parent], root=Path("/"))
        lines = out.strip().split("\n")
        # Find the lines with b and c - c should be more indented
        b_line = next(l for l in lines if "b" in l and "c" not in l)
        c_line = next(l for l in lines if "  c" in l or "/c" in l)
        # c should have more leading spaces than b
        b_indent = len(b_line) - len(b_line.lstrip())
        c_indent = len(c_line) - len(c_line.lstrip())
        assert c_indent > b_indent

    def test_empty_entries(self) -> None:
        out = format_tree([], root=Path("/lib"))
        assert "(empty)" in out

    def test_shows_total(self) -> None:
        entries = [
            TreeEntry(path=Path("/a/x"), size_bytes=1_000_000_000, children=()),
            TreeEntry(path=Path("/a/y"), size_bytes=2_000_000_000, children=()),
        ]
        out = format_tree(entries, root=Path("/a"))
        assert "total" in out

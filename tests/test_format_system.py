"""Tests for system category formatting."""

from __future__ import annotations

from pathlib import Path

from disk_free.formatter import format_category_results
from disk_free.scanner import DirEntry
from disk_free.system import Category, CategoryResult, SafeTarget


def _cat(name: str, targets: tuple[SafeTarget, ...] = ()) -> Category:
    return Category(name=name, description="test desc", targets=targets)


def _target(path: Path) -> SafeTarget:
    return SafeTarget(path=path, description="test item", regenerate_hint="rebuild")


class TestFormatCategoryResults:
    def test_single_category(self) -> None:
        google = Path("~/Library/Caches/Google")
        pip_dir = Path("~/Library/Caches/pip")
        results = [
            CategoryResult(
                category=_cat("Caches", (_target(google), _target(pip_dir))),
                entries=[
                    DirEntry(path=google, size_bytes=7_900_000_000),
                    DirEntry(path=pip_dir, size_bytes=1_100_000_000),
                ],
            ),
        ]
        output = format_category_results(results)
        assert "Caches" in output
        assert "Google" in output
        assert "pip" in output
        assert "total" in output

    def test_multiple_categories(self) -> None:
        derived = Path("/dev/DerivedData")
        google = Path("/cache/Google")
        results = [
            CategoryResult(
                category=_cat("Developer", (_target(derived),)),
                entries=[DirEntry(path=derived, size_bytes=6_000_000_000)],
            ),
            CategoryResult(
                category=_cat("Caches", (_target(google),)),
                entries=[DirEntry(path=google, size_bytes=7_000_000_000)],
            ),
        ]
        output = format_category_results(results)
        assert "Developer" in output
        assert "Caches" in output

    def test_empty_results(self) -> None:
        output = format_category_results([])
        assert "Nothing to show" in output

    def test_shows_category_number(self) -> None:
        p = Path("/cache/x")
        results = [
            CategoryResult(
                category=_cat("Caches", (_target(p),)),
                entries=[DirEntry(path=p, size_bytes=1000)],
            ),
        ]
        output = format_category_results(results)
        assert "[1]" in output

    def test_shows_grand_total(self) -> None:
        a = Path("/a/x")
        b = Path("/b/y")
        results = [
            CategoryResult(
                category=_cat("A", (_target(a),)),
                entries=[DirEntry(path=a, size_bytes=1_000_000_000)],
            ),
            CategoryResult(
                category=_cat("B", (_target(b),)),
                entries=[DirEntry(path=b, size_bytes=2_000_000_000)],
            ),
        ]
        output = format_category_results(results)
        assert "Grand total" in output

    def test_shows_description(self) -> None:
        p = Path("/cache/Google")
        t = SafeTarget(p, "Chrome browser cache", "Chrome recreates on use")
        results = [
            CategoryResult(
                category=Category(name="Caches", description="caches", targets=(t,)),
                entries=[DirEntry(path=p, size_bytes=1000)],
            ),
        ]
        output = format_category_results(results)
        assert "Chrome browser cache" in output

"""Tests for system category scanning."""

from __future__ import annotations

from pathlib import Path

from disk_free.system import (
    Category,
    CategoryResult,
    DEFAULT_CATEGORIES,
    SafeTarget,
    scan_categories,
)


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * size)


def _cat(name: str, targets: tuple[SafeTarget, ...]) -> Category:
    return Category(name=name, description="test", targets=targets)


def _target(path: Path) -> SafeTarget:
    return SafeTarget(path=path, description="test item", regenerate_hint="rebuild")


class TestCategory:
    def test_fields(self) -> None:
        t = SafeTarget(Path("/tmp/x"), "desc", "hint")
        c = Category(name="Caches", description="App caches", targets=(t,))
        assert c.name == "Caches"
        assert len(c.targets) == 1

    def test_default_categories_exist(self) -> None:
        names = {c.name for c in DEFAULT_CATEGORIES}
        assert "Developer" in names
        assert "Caches" in names
        assert "Logs" in names

    def test_default_categories_have_targets(self) -> None:
        for cat in DEFAULT_CATEGORIES:
            assert len(cat.targets) > 0


class TestSafeTarget:
    def test_default_safety_is_safe(self) -> None:
        t = SafeTarget(Path("/tmp/x"), "desc", "hint")
        assert t.safety == "safe"

    def test_caution_safety(self) -> None:
        t = SafeTarget(Path("/tmp/x"), "desc", "hint", safety="caution")
        assert t.safety == "caution"

    def test_some_default_targets_are_caution(self) -> None:
        """Android SDK and VM-like targets should be flagged caution."""
        all_targets = [t for c in DEFAULT_CATEGORIES for t in c.targets]
        has_caution = any(t.safety == "caution" for t in all_targets)
        assert has_caution


class TestCategoryResult:
    def test_total_bytes(self) -> None:
        from disk_free.scanner import DirEntry

        r = CategoryResult(
            category=_cat("Test", ()),
            entries=[
                DirEntry(path=Path("/a"), size_bytes=1000),
                DirEntry(path=Path("/b"), size_bytes=2000),
            ],
        )
        assert r.total_bytes == 3000

    def test_empty_entries(self) -> None:
        r = CategoryResult(category=_cat("Test", ()), entries=[])
        assert r.total_bytes == 0


class TestScanCategories:
    def test_finds_existing_targets(self, tmp_path: Path) -> None:
        google = tmp_path / "Caches" / "Google"
        pip_dir = tmp_path / "Caches" / "pip"
        _make_file(google / "data.bin", size=5000)
        _make_file(pip_dir / "cache.bin", size=3000)

        categories = [_cat("Caches", (_target(google), _target(pip_dir)))]
        results = scan_categories(categories)

        assert len(results) == 1
        assert results[0].category.name == "Caches"
        assert len(results[0].entries) == 2
        assert results[0].total_bytes > 0

    def test_skips_nonexistent_targets(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope"
        categories = [_cat("Gone", (_target(missing),))]
        results = scan_categories(categories)
        assert len(results) == 0

    def test_skips_empty_targets(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir(parents=True)

        categories = [_cat("Empty", (_target(empty_dir),))]
        results = scan_categories(categories)
        assert len(results) == 0

    def test_multiple_categories(self, tmp_path: Path) -> None:
        derived = tmp_path / "Developer" / "DerivedData"
        google = tmp_path / "Caches" / "Google"
        _make_file(derived / "x.o", size=2000)
        _make_file(google / "y.bin", size=1000)

        categories = [
            _cat("Developer", (_target(derived),)),
            _cat("Caches", (_target(google),)),
        ]
        results = scan_categories(categories)
        assert len(results) == 2
        assert {r.category.name for r in results} == {"Developer", "Caches"}

    def test_entries_sorted_largest_first(self, tmp_path: Path) -> None:
        small = tmp_path / "small"
        large = tmp_path / "large"
        _make_file(small / "a.bin", size=100)
        _make_file(large / "b.bin", size=5000)

        categories = [_cat("Test", (_target(small), _target(large)))]
        results = scan_categories(categories)

        entries = results[0].entries
        assert entries[0].size_bytes >= entries[1].size_bytes

    def test_on_scan_callback(self, tmp_path: Path) -> None:
        target_path = tmp_path / "x"
        _make_file(target_path / "a.bin")

        scanned: list[str] = []
        categories = [_cat("Caches", (_target(target_path),))]
        scan_categories(categories, on_scan=lambda name, p: scanned.append(name))

        assert "Caches" in scanned

    def test_mixes_existing_and_missing(self, tmp_path: Path) -> None:
        existing = tmp_path / "exists"
        missing = tmp_path / "missing"
        _make_file(existing / "a.bin", size=1000)

        categories = [_cat("Mixed", (_target(existing), _target(missing)))]
        results = scan_categories(categories)
        assert len(results) == 1
        assert len(results[0].entries) == 1

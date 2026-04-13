"""Scan macOS system directories for safe-to-remove items, grouped by category."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .scanner import DirEntry, dir_size

ScanCategoryCallback = Callable[[str, Path], None]


@dataclass(frozen=True)
class SafeTarget:
    """A specific directory known to be safe to remove."""

    path: Path
    description: str
    regenerate_hint: str


@dataclass(frozen=True)
class Category:
    """A group of safe-to-remove targets."""

    name: str
    description: str
    targets: tuple[SafeTarget, ...]


@dataclass(frozen=True)
class CategoryResult:
    """Scan result for one category — only targets that exist and have size."""

    category: Category
    entries: list[DirEntry]

    @property
    def total_bytes(self) -> int:
        return sum(e.size_bytes for e in self.entries)


HOME = Path.home()

DEFAULT_CATEGORIES: list[Category] = [
    Category(
        name="Developer",
        description="Xcode build caches and simulators",
        targets=(
            SafeTarget(
                HOME / "Library" / "Developer" / "Xcode" / "DerivedData",
                "Xcode build cache",
                "Rebuilds automatically on next build",
            ),
            SafeTarget(
                HOME / "Library" / "Developer" / "Xcode" / "Archives",
                "Xcode archived builds",
                "Re-archive from Xcode",
            ),
            SafeTarget(
                HOME / "Library" / "Developer" / "Xcode" / "iOS DeviceSupport",
                "iOS device debug symbols",
                "Re-downloaded when device connects",
            ),
            SafeTarget(
                HOME / "Library" / "Developer" / "CoreSimulator" / "Caches",
                "Simulator caches",
                "xcrun simctl delete unavailable",
            ),
        ),
    ),
    Category(
        name="Caches",
        description="App caches (safe to remove, apps recreate on demand)",
        targets=(
            SafeTarget(
                HOME / "Library" / "Caches" / "Google",
                "Chrome browser cache",
                "Chrome recreates on use",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "typescript",
                "TypeScript compiler cache",
                "Recreated on next compile",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "pip",
                "pip download cache",
                "pip re-downloads on install",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "ms-playwright",
                "Playwright browser binaries",
                "npx playwright install",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "CocoaPods",
                "CocoaPods spec cache",
                "pod cache clean --all",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "Homebrew",
                "Homebrew download cache",
                "brew cleanup",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "pnpm",
                "pnpm store cache",
                "pnpm store prune",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "Yarn",
                "Yarn cache",
                "yarn cache clean",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.apple.python",
                "Apple Python cache",
                "Auto-regenerated",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "SiriTTS",
                "Siri text-to-speech cache",
                "Auto-regenerated",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.spotify.client",
                "Spotify cache",
                "Spotify recreates on use",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.microsoft.VSCode",
                "VS Code cache",
                "VS Code recreates on launch",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.google.SoftwareUpdate",
                "Google updater cache",
                "Auto-regenerated",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "node-gyp",
                "node-gyp compilation cache",
                "Recreated on native module install",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "ms-playwright-go",
                "Playwright Go browser binaries",
                "go run github.com/playwright-community/playwright-go/cmd/playwright install",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "Jedi",
                "Python Jedi autocomplete cache",
                "Auto-regenerated",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.tdesktop.Telegram",
                "Telegram desktop cache",
                "Telegram recreates on use",
            ),
        ),
    ),
    Category(
        name="Logs",
        description="Application and system log files",
        targets=(
            SafeTarget(
                HOME / "Library" / "Logs" / "Google",
                "Google app logs",
                "Auto-generated",
            ),
            SafeTarget(
                HOME / "Library" / "Logs" / "JetBrains",
                "JetBrains IDE logs",
                "Auto-generated",
            ),
            SafeTarget(
                HOME / "Library" / "Logs" / "CoreSimulator",
                "iOS Simulator logs",
                "Auto-generated",
            ),
            SafeTarget(
                HOME / "Library" / "Logs" / "DiagnosticReports",
                "macOS crash reports",
                "Auto-generated",
            ),
        ),
    ),
]


def scan_categories(
    categories: list[Category],
    *,
    on_scan: ScanCategoryCallback | None = None,
) -> list[CategoryResult]:
    """Scan safe targets in each category. Only returns targets that exist with size > 0."""
    results: list[CategoryResult] = []

    for cat in categories:
        entries: list[DirEntry] = []

        for target in cat.targets:
            if on_scan is not None:
                on_scan(cat.name, target.path)

            if not target.path.exists() or not target.path.is_dir():
                continue

            try:
                size = dir_size(target.path)
            except PermissionError:
                continue

            if size > 0:
                entries.append(DirEntry(path=target.path, size_bytes=size))

        entries.sort(key=lambda e: e.size_bytes, reverse=True)

        if entries:
            results.append(CategoryResult(category=cat, entries=entries))

    return results

"""Scan macOS system directories for safe-to-remove items, grouped by category."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .scanner import DirEntry, dir_size

ScanCategoryCallback = Callable[[str, Path], None]


@dataclass(frozen=True)
class SafeTarget:
    """A specific directory known to be removable.

    *safety* is ``"safe"`` (purely regenerable — caches, build outputs)
    or ``"caution"`` (removable but may contain user work or require
    significant re-download — e.g. emulator images, VM disks, NDK).
    """

    path: Path
    description: str
    regenerate_hint: str
    safety: str = "safe"


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
            SafeTarget(
                HOME / "Library" / "Caches" / "com.google.antigravity.ShipIt",
                "Antigravity updater download cache",
                "App re-downloads next update",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "dev.kiro.desktop.ShipIt",
                "Kiro updater download cache",
                "App re-downloads next update",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.electron.ollama.ShipIt",
                "Ollama updater download cache",
                "App re-downloads next update",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "ledger-live-desktop-updater",
                "Ledger Live updater cache",
                "App re-downloads next update",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "termius-updater",
                "Termius updater cache",
                "App re-downloads next update",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "redisinsight-updater",
                "RedisInsight updater cache",
                "App re-downloads next update",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "com.openai.atlas",
                "OpenAI Atlas cache",
                "App recreates on use",
            ),
            SafeTarget(
                HOME / "Library" / "Caches" / "Steam",
                "Steam client cache",
                "Steam recreates on launch",
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
    Category(
        name="Dev Tool Caches",
        description="Package managers and language toolchain caches",
        targets=(
            SafeTarget(
                HOME / ".npm" / "_cacache",
                "npm package cache",
                "npm re-downloads on install",
            ),
            SafeTarget(
                HOME / ".cache" / "uv",
                "uv (Python) package cache",
                "uv re-downloads on install",
            ),
            SafeTarget(
                HOME / ".cache" / "puppeteer",
                "Puppeteer Chromium/Chrome binaries",
                "npx puppeteer browsers install chrome",
            ),
            SafeTarget(
                HOME / ".yarn" / "berry" / "cache",
                "Yarn Berry package cache",
                "yarn install re-downloads",
            ),
            SafeTarget(
                HOME / ".bun" / "install" / "cache",
                "Bun package cache",
                "bun install re-downloads",
            ),
            SafeTarget(
                HOME / ".cache" / "huggingface" / "hub",
                "HuggingFace model cache",
                "Re-downloaded on first use",
            ),
            SafeTarget(
                HOME / ".cache" / "prisma",
                "Prisma query engine cache",
                "npx prisma generate re-downloads",
            ),
            SafeTarget(
                HOME / ".minikube" / "cache",
                "minikube ISO + preloaded images",
                "minikube re-downloads on start",
            ),
            SafeTarget(
                HOME / ".serverless" / "releases",
                "Serverless Framework binaries",
                "Re-downloaded on first run",
            ),
            SafeTarget(
                HOME / ".expo" / "expo-go",
                "Expo Go dev client",
                "Re-downloaded on expo start",
            ),
            SafeTarget(
                HOME / ".expo" / "ios-simulator-app-cache",
                "Expo iOS simulator app cache",
                "Re-downloaded on next simulator run",
            ),
            SafeTarget(
                HOME / ".expo" / "android-apk-cache",
                "Expo Android APK cache",
                "Re-downloaded on next build",
            ),
        ),
    ),
    Category(
        name="Android SDK",
        description="Android SDK components — review before removing",
        targets=(
            SafeTarget(
                HOME / "Library" / "Android" / "sdk" / "system-images",
                "Emulator OS images — per API level × architecture",
                "Re-download via Android Studio SDK Manager; only needed if you run those emulators",
                safety="caution",
            ),
            SafeTarget(
                HOME / "Library" / "Android" / "sdk" / "ndk",
                "Native Development Kit (C/C++ toolchain)",
                "Re-download via SDK Manager; needed for React Native / native Android",
                safety="caution",
            ),
            SafeTarget(
                HOME / "Library" / "Android" / "sdk" / "build-tools",
                "Build tools (multiple versions)",
                "Re-download via SDK Manager; latest version is usually enough",
                safety="caution",
            ),
            SafeTarget(
                HOME / "Library" / "Android" / "sdk" / "platforms",
                "Android SDK platforms (per API level)",
                "Re-download via SDK Manager; only keep API levels you target",
                safety="caution",
            ),
            SafeTarget(
                HOME / "Library" / "Android" / "sdk" / "sources",
                "Android framework source code (for IDE nav)",
                "Re-download via SDK Manager",
                safety="caution",
            ),
            SafeTarget(
                HOME / "Library" / "Android" / "sdk" / "cmake",
                "CMake for native Android builds",
                "Re-download via SDK Manager; only needed for NDK builds",
                safety="caution",
            ),
        ),
    ),
    Category(
        name="App VMs & User Data",
        description="Virtual machines and app-local persistent data",
        targets=(
            SafeTarget(
                HOME / "Library" / "Application Support" / "Claude" / "vm_bundles",
                "Claude Desktop VM disk images (rootfs + session data)",
                "Claude recreates fresh VMs on next use — deletes any work done in Claude's computer-use agent",
                safety="caution",
            ),
            SafeTarget(
                HOME / ".android" / "avd",
                "Android emulator virtual devices (AVDs)",
                "Re-create in Android Studio AVD Manager — any installed apps and data in the emulator are lost",
                safety="caution",
            ),
            SafeTarget(
                HOME / ".gemini" / "antigravity" / "browser_recordings",
                "Antigravity browser session recordings",
                "Recordings are lost — re-run the sessions to regenerate",
                safety="caution",
            ),
            SafeTarget(
                HOME / ".rustup" / "toolchains",
                "Rust toolchains (multiple versions installed)",
                "rustup install <version> per toolchain — okay to delete all but the active one",
                safety="caution",
            ),
            SafeTarget(
                HOME / ".nvm" / "versions" / "node",
                "Node.js versions installed via nvm",
                "nvm install <version> per version — okay to delete versions you don't use",
                safety="caution",
            ),
            SafeTarget(
                HOME / ".vscode" / "extensions",
                "VS Code extensions",
                "Re-install from Marketplace — extension settings preserved in user profile",
                safety="caution",
            ),
            SafeTarget(
                HOME / ".cursor" / "extensions",
                "Cursor extensions",
                "Re-install from Marketplace",
                safety="caution",
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

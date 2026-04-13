"""Detect removable build artifacts and dependency caches."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .scanner import dir_size

ScanCallback = Callable[[Path], None]
RemoveCallback = Callable[[int, int, "Artifact"], None]


@dataclass(frozen=True)
class ArtifactRule:
    """A pattern that identifies a removable directory."""

    dir_name: str
    description: str
    regenerate_hint: str


ARTIFACT_RULES: tuple[ArtifactRule, ...] = (
    # JavaScript / TypeScript
    ArtifactRule("node_modules", "npm/yarn/pnpm dependencies", "npm install"),
    ArtifactRule(".next", "Next.js build output", "npm run build"),
    ArtifactRule(".nuxt", "Nuxt.js build output", "npm run build"),
    ArtifactRule(".svelte-kit", "SvelteKit build output", "npm run build"),
    ArtifactRule(".angular", "Angular cache", "ng build"),
    ArtifactRule(".astro", "Astro build output", "npm run build"),
    ArtifactRule(".vite", "Vite cache", "vite build"),
    ArtifactRule(".parcel-cache", "Parcel cache", "parcel build"),
    ArtifactRule(".cache", "Generic build tool cache", "re-run build"),
    ArtifactRule(".expo", "Expo cache", "npx expo start"),
    ArtifactRule(".turbo", "Turborepo cache", "turbo run build"),
    ArtifactRule("dist", "Build output", "npm run build"),
    ArtifactRule("build", "Build output", "npm run build"),
    ArtifactRule("out", "Build output (Next.js export / IntelliJ)", "re-run build"),
    # Python
    ArtifactRule(".venv", "Python virtual environment", "python -m venv .venv && pip install -r requirements.txt"),
    ArtifactRule("venv", "Python virtual environment", "python -m venv venv && pip install -r requirements.txt"),
    ArtifactRule("__pycache__", "Python bytecode cache", "auto-generated on import"),
    ArtifactRule(".pytest_cache", "pytest cache", "auto-generated on test run"),
    ArtifactRule(".mypy_cache", "mypy type-check cache", "auto-generated on mypy run"),
    ArtifactRule(".ruff_cache", "ruff lint cache", "auto-generated on ruff run"),
    ArtifactRule(".tox", "tox environments", "tox"),
    ArtifactRule(".nox", "nox environments", "nox"),
    ArtifactRule("htmlcov", "coverage.py HTML report", "coverage html"),
    ArtifactRule(".eggs", "setuptools build artifacts", "auto-generated on install"),
    # Rust / Go / Java / Kotlin
    ArtifactRule("target", "Rust/Java/Scala build output", "cargo build / mvn compile / sbt compile"),
    ArtifactRule(".gradle", "Gradle cache", "gradle build"),
    # iOS / Swift / macOS
    ArtifactRule("Pods", "CocoaPods dependencies", "pod install"),
    ArtifactRule("DerivedData", "Xcode derived data", "auto-generated on Xcode build"),
    ArtifactRule(".build", "Swift Package Manager build output", "swift build"),
    # .NET / C#
    ArtifactRule("bin", ".NET/C++ build output", "dotnet build"),
    ArtifactRule("obj", ".NET intermediate build output", "dotnet build"),
    # Flutter / Dart
    ArtifactRule(".dart_tool", "Dart/Flutter build cache", "flutter pub get"),
    # Ruby
    ArtifactRule(".bundle", "Bundler config/cache", "bundle install"),
    # Elixir
    ArtifactRule("_build", "Elixir/Mix build output", "mix compile"),
    ArtifactRule("deps", "Elixir/Mix dependencies", "mix deps.get"),
    # Haskell
    ArtifactRule(".stack-work", "Haskell Stack build output", "stack build"),
    ArtifactRule("dist-newstyle", "Cabal build output", "cabal build"),
    # Zig
    ArtifactRule("zig-cache", "Zig build cache", "zig build"),
    ArtifactRule("zig-out", "Zig build output", "zig build"),
    # Clojure
    ArtifactRule(".cpcache", "Clojure CLI classpath cache", "auto-generated on clj run"),
    # Jupyter
    ArtifactRule(".ipynb_checkpoints", "Jupyter notebook checkpoints", "auto-generated on save"),
    # Terraform
    ArtifactRule(".terraform", "Terraform provider/module cache", "terraform init"),
)

_ARTIFACT_NAMES: frozenset[str] = frozenset(r.dir_name for r in ARTIFACT_RULES)
_RULES_BY_NAME: dict[str, ArtifactRule] = {r.dir_name: r for r in ARTIFACT_RULES}


@dataclass(frozen=True)
class Artifact:
    """A detected artifact directory with its size."""

    path: Path
    size_bytes: int
    rule_name: str
    regenerate_hint: str


@dataclass(frozen=True)
class CleanResult:
    """Summary of a clean operation."""

    removed: int
    failed: int
    bytes_freed: int
    errors: list[str] = field(default_factory=list)


def clean_artifacts(
    artifacts: list[Artifact],
    *,
    on_remove: RemoveCallback | None = None,
) -> CleanResult:
    """Remove artifact directories from disk. Returns a summary."""
    removed = 0
    failed = 0
    bytes_freed = 0
    errors: list[str] = []
    total = len(artifacts)

    for i, artifact in enumerate(artifacts, 1):
        if on_remove is not None:
            on_remove(i, total, artifact)
        try:
            if artifact.path.exists():
                shutil.rmtree(artifact.path)
            removed += 1
            bytes_freed += artifact.size_bytes
        except OSError as e:
            failed += 1
            errors.append(f"{artifact.path}: {e}")

    return CleanResult(
        removed=removed,
        failed=failed,
        bytes_freed=bytes_freed,
        errors=errors,
    )


def find_artifacts(
    root: Path,
    *,
    on_scan: ScanCallback | None = None,
) -> list[Artifact]:
    """Walk *root* and return removable artifact directories, sorted largest first.

    Does not descend into artifact directories themselves, so nested
    ``node_modules/pkg/node_modules`` is counted once under the outermost match.
    """
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    artifacts: list[Artifact] = []
    _walk(root, artifacts, on_scan)
    artifacts.sort(key=lambda a: a.size_bytes, reverse=True)
    return artifacts


def _walk(
    directory: Path,
    out: list[Artifact],
    on_scan: ScanCallback | None = None,
) -> None:
    """Recursively scan *directory*, collecting artifacts into *out*.

    Skips symlinks to avoid loops (e.g. Steam.app has self-referential
    symlinks that produce infinite path nesting).
    """
    try:
        children = sorted(directory.iterdir())
    except (PermissionError, OSError):
        return

    for child in children:
        try:
            if child.is_symlink() or not child.is_dir():
                continue
        except OSError:
            continue

        if on_scan is not None:
            on_scan(child)

        name = child.name
        if name in _ARTIFACT_NAMES:
            rule = _RULES_BY_NAME[name]
            out.append(
                Artifact(
                    path=child,
                    size_bytes=dir_size(child),
                    rule_name=rule.dir_name,
                    regenerate_hint=rule.regenerate_hint,
                )
            )
            # don't descend into artifact dirs
        else:
            _walk(child, out, on_scan)

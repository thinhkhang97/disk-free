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
    ArtifactRule("node_modules", "npm/yarn dependencies", "npm install"),
    ArtifactRule(".next", "Next.js build output", "npm run build"),
    ArtifactRule("dist", "Build output", "npm run build"),
    ArtifactRule("build", "Build output", "npm run build"),
    ArtifactRule(".venv", "Python virtual environment", "python -m venv .venv && pip install -r requirements.txt"),
    ArtifactRule("venv", "Python virtual environment", "python -m venv venv && pip install -r requirements.txt"),
    ArtifactRule("__pycache__", "Python bytecode cache", "auto-generated on import"),
    ArtifactRule(".expo", "Expo cache", "npx expo start"),
    ArtifactRule(".turbo", "Turborepo cache", "turbo run build"),
    ArtifactRule("target", "Rust/Java build output", "cargo build / mvn compile"),
    ArtifactRule(".gradle", "Gradle cache", "gradle build"),
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

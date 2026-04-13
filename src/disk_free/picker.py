"""Interactive picker for selecting items to remove.

Uses the ``questionary`` library for the actual interactive UI (multi-select
with arrow navigation, checkbox toggle, scrolling, etc). This module wraps
the library with our domain types (PickerItem, safety flags, grouping).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import questionary
from questionary import Choice, Separator

from .formatter import human_size


@dataclass(frozen=True)
class PickerItem:
    """An item that can be selected for removal.

    *safety* is ``"safe"`` (clearly regenerable — caches, build artifacts)
    or ``"caution"`` (removable but may contain user work, specific
    configurations, or large re-downloads — e.g. VM disk images, emulator
    system images, NDK toolchains).
    """

    path: Path
    size_bytes: int
    label: str
    description: str
    hint: str
    group: str = ""
    safety: str = "safe"


def _format_choice_title(item: PickerItem) -> str:
    """Build the visible text for a single choice row."""
    size = human_size(item.size_bytes)
    marker = "⚠ " if item.safety == "caution" else "  "
    # size | label | description | hint
    return (
        f"{marker}{size:>6}  {item.label:<30}  "
        f"{item.description}  ·  restore: {item.hint}"
    )


def _build_choices(items: list[PickerItem]) -> list[Choice | Separator]:
    """Convert picker items to questionary choices with group separators.

    A non-selectable Separator is inserted whenever the group changes.
    Caution-flagged groups are labelled so they stand out.
    """
    choices: list[Choice | Separator] = []
    current_group: str | None = None

    # Pre-compute which groups contain any caution items
    caution_groups = {
        item.group for item in items
        if item.safety == "caution" and item.group
    }

    for idx, item in enumerate(items):
        if item.group and item.group != current_group:
            current_group = item.group
            if item.group in caution_groups:
                choices.append(Separator(f"── {item.group}  (⚠ CAUTION) ──"))
            else:
                choices.append(Separator(f"── {item.group} ──"))

        choices.append(
            Choice(
                title=_format_choice_title(item),
                value=idx,
                checked=False,
            )
        )

    return choices


def run_picker(items: list[PickerItem]) -> list[PickerItem] | None:
    """Show an interactive multi-select picker.

    Returns the selected items, or ``None`` if the user cancelled (Ctrl+C
    or stdin isn't a terminal).
    """
    if not items:
        return []

    if not sys.stdin.isatty():
        return None

    total = sum(item.size_bytes for item in items)
    prompt = (
        f"Select items to remove ({len(items)} found, {human_size(total)} total). "
        "↑↓ navigate · SPACE toggle · a all · i invert · ENTER confirm · Ctrl+C cancel"
    )

    try:
        selected_indices = questionary.checkbox(
            prompt,
            choices=_build_choices(items),
            qmark="",
            instruction=" ",
        ).ask()
    except KeyboardInterrupt:
        return None

    if selected_indices is None:
        return None

    return [items[i] for i in selected_indices]

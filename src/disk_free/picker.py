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
from prompt_toolkit.formatted_text import FormattedText
from questionary import Choice, Separator, Style

from .formatter import human_size

# Color scheme for the picker UI. Keys are style classes used in
# FormattedText tuples below and in the questionary prompt chrome.
_PICKER_STYLE = Style(
    [
        # Chrome (questionary's own parts)
        ("qmark", "fg:ansicyan bold"),
        ("question", "bold"),
        ("pointer", "fg:ansicyan bold"),
        ("highlighted", "fg:ansicyan bold"),
        ("selected", "fg:ansigreen bold"),
        ("separator", "fg:ansiblue bold"),
        ("instruction", "fg:ansibrightblack"),
        ("text", ""),
        ("answer", "fg:ansigreen bold"),
        # Our custom classes for item content
        ("item-caution-mark", "fg:ansiyellow bold"),
        ("item-size-big", "fg:ansired bold"),
        ("item-size-med", "fg:ansiyellow bold"),
        ("item-size-sm", "fg:ansigreen"),
        ("item-label", "bold"),
        ("item-desc", "fg:ansibrightblack"),
        ("item-hint", "fg:ansibrightblack italic"),
        ("item-caution-label", "fg:ansiyellow"),
        ("sep-caution", "fg:ansiyellow bold"),
        ("sep-safe", "fg:ansiblue bold"),
    ]
)

_GB = 1024**3
_100_MB = 100 * 1024**2


def _size_class(size_bytes: int) -> str:
    """Return style class name based on size magnitude."""
    if size_bytes >= _GB:
        return "class:item-size-big"
    if size_bytes >= _100_MB:
        return "class:item-size-med"
    return "class:item-size-sm"


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


def _format_choice_title(item: PickerItem) -> FormattedText:
    """Build a colorized FormattedText title for a single choice row.

    Layout:
    ``⚠ 20.9G  system-images           Emulator OS images · restore: ...``

    Colors:
    - caution mark: yellow
    - size: red (≥1G), yellow (≥100M), green (<100M)
    - label: bold
    - description: dim
    - hint: dim italic
    """
    size = human_size(item.size_bytes)
    parts: list[tuple[str, str]] = []

    # Caution marker (2 visible chars wide for alignment)
    if item.safety == "caution":
        parts.append(("class:item-caution-mark", "⚠ "))
    else:
        parts.append(("", "  "))

    # Size — colored by magnitude
    parts.append((_size_class(item.size_bytes), f"{size:>6}"))
    parts.append(("", "  "))

    # Label — bold (yellow if caution). Min width 30, grows as needed.
    label_class = "class:item-caution-label" if item.safety == "caution" else "class:item-label"
    label_text = item.label if len(item.label) >= 30 else f"{item.label:<30}"
    parts.append((label_class, label_text))
    parts.append(("", "  "))

    # Description and hint — dim
    parts.append(("class:item-desc", item.description))
    parts.append(("class:item-hint", f"  ·  restore: {item.hint}"))

    return FormattedText(parts)


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
                sep_title = FormattedText(
                    [("class:sep-caution", f"── {item.group}  (⚠ CAUTION) ──")]
                )
            else:
                sep_title = FormattedText(
                    [("class:sep-safe", f"── {item.group} ──")]
                )
            choices.append(Separator(sep_title))

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
            style=_PICKER_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return None

    if selected_indices is None:
        return None

    return [items[i] for i in selected_indices]

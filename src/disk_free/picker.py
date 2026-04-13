"""Interactive terminal picker for selecting items to remove."""

from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import tty
from dataclasses import dataclass
from pathlib import Path

from .formatter import human_size

# Header (2) + blank (1) + footer (2) + blank (1) = 6 reserved lines
_RESERVED_LINES = 6


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


class PickerState:
    """Mutable state for the picker UI."""

    def __init__(
        self,
        items: list[PickerItem],
        viewport_height: int | None = None,
    ) -> None:
        self.items = items
        self.selected: set[int] = set()
        self.cursor: int = 0
        self.scroll_offset: int = 0
        self.viewport_height: int = viewport_height or 20

    def move(self, delta: int) -> None:
        if not self.items:
            return
        self.cursor = max(0, min(len(self.items) - 1, self.cursor + delta))
        # Adjust scroll to keep cursor visible
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.viewport_height:
            self.scroll_offset = self.cursor - self.viewport_height + 1

    def toggle(self, index: int) -> None:
        if index in self.selected:
            self.selected.discard(index)
        else:
            self.selected.add(index)

    def toggle_all(self) -> None:
        if len(self.selected) == len(self.items):
            self.selected.clear()
        else:
            self.selected = set(range(len(self.items)))

    def selected_items(self) -> list[PickerItem]:
        return [self.items[i] for i in sorted(self.selected)]

    @property
    def selected_bytes(self) -> int:
        return sum(self.items[i].size_bytes for i in self.selected)


def render_picker(state: PickerState, *, term_width: int = 80) -> list[str]:
    """Pure function: render the picker display as a list of lines."""
    if not state.items:
        return ["  Nothing to remove."]

    lines: list[str] = []

    # Header
    total = sum(item.size_bytes for item in state.items)
    sel_count = len(state.selected)
    sel_bytes = state.selected_bytes
    lines.append(
        f"  {sel_count}/{len(state.items)} selected"
        f" ({human_size(sel_bytes)} of {human_size(total)})"
    )
    lines.append("")

    # Build item lines with group headers
    item_lines: list[tuple[int | None, str]] = []  # (item_index | None for header, line)
    current_group = None
    for i, item in enumerate(state.items):
        if item.group and item.group != current_group:
            current_group = item.group
            item_lines.append((None, f"  {item.group}"))

        marker = ">" if i == state.cursor else " "
        check = "[x]" if i in state.selected else "[ ]"
        size = human_size(item.size_bytes)
        flag = "⚠" if item.safety == "caution" else " "

        line = f"  {marker} {check} {flag} {size:>5}  {item.label:<28} {item.description}"
        # Truncate to terminal width
        if len(line) > term_width:
            line = line[: term_width - 1]
        item_lines.append((i, line))

    # Apply viewport scrolling
    # We need to figure out which item_lines correspond to the visible viewport
    # Map item indices to line positions
    visible_start = state.scroll_offset
    visible_end = state.scroll_offset + state.viewport_height

    # Find line range that covers visible items
    first_line = 0
    last_line = len(item_lines)
    for li, (idx, _) in enumerate(item_lines):
        if idx is not None and idx == visible_start:
            # Include preceding group header if any
            if li > 0 and item_lines[li - 1][0] is None:
                first_line = li - 1
            else:
                first_line = li
            break

    for li in range(len(item_lines) - 1, -1, -1):
        idx, _ = item_lines[li]
        if idx is not None and idx < visible_end:
            last_line = li + 1
            break

    for _, line in item_lines[first_line:last_line]:
        lines.append(line)

    # Hint line for current item
    lines.append("")
    if 0 <= state.cursor < len(state.items):
        cur = state.items[state.cursor]
        prefix = "  ⚠ CAUTION: " if cur.safety == "caution" else "  Restore: "
        lines.append(f"{prefix}{cur.hint}")

    # Footer
    lines.append("")
    lines.append("  \033[2m↑↓ move  SPACE select  a all  ENTER remove  ESC cancel\033[0m")

    return lines


def _read_key(fd: int) -> str:
    """Read a keypress from *fd*, handling escape sequences for arrow keys.

    Uses ``os.read`` on the file descriptor directly to bypass Python's
    stdin buffering (which would break ``select()``-based lookahead for
    multi-byte escape sequences like arrow keys).
    """
    data = os.read(fd, 1)
    # Drain any additional bytes sent as part of the same key press
    # (e.g. arrow keys send 3 bytes: ESC [ A).
    while select.select([fd], [], [], 0.01)[0]:
        more = os.read(fd, 1)
        if not more:
            break
        data += more

    s = data.decode("utf-8", errors="ignore")

    if s == "\x1b[A":
        return "UP"
    if s == "\x1b[B":
        return "DOWN"
    if s == "\x1b":
        return "ESC"
    if s == " ":
        return "SPACE"
    if s in ("\r", "\n"):
        return "ENTER"
    if s == "\x03":  # Ctrl+C
        return "ESC"
    return s


def run_picker(items: list[PickerItem]) -> list[PickerItem] | None:
    """Show interactive picker. Returns selected items, or None if cancelled.

    Falls back to None if stdin is not a terminal.

    Uses DEC cursor save/restore (``\\0337`` / ``\\0338``) rather than
    counting drawn lines — this avoids cursor-math bugs when the picker
    is near the bottom of the terminal and ``\\r\\n`` causes scrolling.
    """
    if not items:
        return []

    if not sys.stdin.isatty():
        return None

    term_size = shutil.get_terminal_size((80, 24))
    term_h, term_w = term_size.lines, term_size.columns
    viewport = max(5, term_h - _RESERVED_LINES - 2)

    state = PickerState(items, viewport_height=viewport)

    # Reserve space: print enough blank lines to force scroll if we're near
    # the bottom, then move back up and save that cursor position.
    reserve = viewport + _RESERVED_LINES
    sys.stderr.write("\n" * reserve)
    sys.stderr.write(f"\033[{reserve}A")
    sys.stderr.write("\0337")  # save cursor (DEC)
    sys.stderr.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        sys.stderr.write("\033[?25l")  # hide cursor
        sys.stderr.flush()

        while True:
            lines = render_picker(state, term_width=term_w)

            # Restore saved position, then clear everything from here to
            # end of screen. This guarantees a clean slate regardless of
            # what was drawn in the previous frame.
            sys.stderr.write("\0338\033[J")

            # Write lines separated by \r\n (raw mode requires both).
            for i, line in enumerate(lines):
                if i > 0:
                    sys.stderr.write("\r\n")
                sys.stderr.write(line)
            sys.stderr.flush()

            key = _read_key(fd)

            if key == "UP":
                state.move(-1)
            elif key == "DOWN":
                state.move(1)
            elif key == "SPACE":
                state.toggle(state.cursor)
            elif key == "a":
                state.toggle_all()
            elif key == "ENTER":
                break
            elif key == "ESC" or key == "q":
                state.selected.clear()
                break

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # Restore cursor position and clear picker area
        sys.stderr.write("\0338\033[J")
        sys.stderr.write("\033[?25h")  # show cursor
        sys.stderr.flush()

    return state.selected_items()

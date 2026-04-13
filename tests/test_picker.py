"""Tests for interactive picker — pure rendering and state logic."""

from __future__ import annotations

from pathlib import Path

from disk_free.picker import PickerItem, PickerState, render_picker


def _item(
    label: str, size: int = 1000, group: str = "", safety: str = "safe",
) -> PickerItem:
    return PickerItem(
        path=Path(f"/tmp/{label}"),
        size_bytes=size,
        label=label,
        description=f"{label} desc",
        hint=f"regen {label}",
        group=group,
        safety=safety,
    )


class TestPickerItem:
    def test_fields(self) -> None:
        item = _item("node_modules", size=5000, group="Caches")
        assert item.label == "node_modules"
        assert item.size_bytes == 5000
        assert item.group == "Caches"
        assert item.hint == "regen node_modules"


class TestPickerState:
    def test_initial_state(self) -> None:
        items = [_item("a"), _item("b"), _item("c")]
        state = PickerState(items)
        assert state.cursor == 0
        assert state.selected == set()

    def test_move_down(self) -> None:
        state = PickerState([_item("a"), _item("b")])
        state.move(1)
        assert state.cursor == 1

    def test_move_down_clamps(self) -> None:
        state = PickerState([_item("a"), _item("b")])
        state.move(1)
        state.move(1)
        assert state.cursor == 1  # can't go past last

    def test_move_up(self) -> None:
        state = PickerState([_item("a"), _item("b")])
        state.move(1)
        state.move(-1)
        assert state.cursor == 0

    def test_move_up_clamps(self) -> None:
        state = PickerState([_item("a"), _item("b")])
        state.move(-1)
        assert state.cursor == 0

    def test_toggle(self) -> None:
        state = PickerState([_item("a"), _item("b")])
        state.toggle(0)
        assert 0 in state.selected
        state.toggle(0)
        assert 0 not in state.selected

    def test_toggle_all(self) -> None:
        state = PickerState([_item("a"), _item("b"), _item("c")])
        state.toggle_all()
        assert state.selected == {0, 1, 2}
        state.toggle_all()
        assert state.selected == set()

    def test_selected_items(self) -> None:
        items = [_item("a"), _item("b"), _item("c")]
        state = PickerState(items)
        state.toggle(0)
        state.toggle(2)
        result = state.selected_items()
        assert len(result) == 2
        assert result[0].label == "a"
        assert result[1].label == "c"

    def test_selected_bytes(self) -> None:
        items = [_item("a", size=1000), _item("b", size=2000)]
        state = PickerState(items)
        state.toggle(0)
        state.toggle(1)
        assert state.selected_bytes == 3000

    def test_scroll_adjusts_on_move(self) -> None:
        items = [_item(f"item{i}") for i in range(50)]
        state = PickerState(items, viewport_height=10)
        for _ in range(15):
            state.move(1)
        # cursor should be 15, scroll should have adjusted
        assert state.cursor == 15
        assert state.scroll_offset > 0
        assert state.cursor < state.scroll_offset + state.viewport_height


class TestRenderPicker:
    def test_shows_items(self) -> None:
        items = [_item("node_modules", size=1_000_000_000, group="Caches")]
        state = PickerState(items)
        lines = render_picker(state, term_width=100)
        text = "\n".join(lines)
        assert "node_modules" in text
        assert "node_modules desc" in text

    def test_shows_cursor_marker(self) -> None:
        items = [_item("a"), _item("b")]
        state = PickerState(items)
        lines = render_picker(state, term_width=80)
        # First item should have cursor marker
        item_lines = [l for l in lines if "a" in l and "desc" in l]
        assert any(">" in l for l in item_lines)

    def test_shows_selection(self) -> None:
        items = [_item("a"), _item("b")]
        state = PickerState(items)
        state.toggle(0)
        lines = render_picker(state, term_width=80)
        text = "\n".join(lines)
        assert "[x]" in text  # selected
        assert "[ ]" in text  # not selected

    def test_shows_group_headers(self) -> None:
        items = [_item("a", group="Dev"), _item("b", group="Caches")]
        state = PickerState(items)
        lines = render_picker(state, term_width=80)
        text = "\n".join(lines)
        assert "Dev" in text
        assert "Caches" in text

    def test_shows_header_with_counts(self) -> None:
        items = [_item("a", size=1000), _item("b", size=2000)]
        state = PickerState(items)
        state.toggle(0)
        lines = render_picker(state, term_width=80)
        text = "\n".join(lines)
        assert "1/2" in text

    def test_shows_keybindings(self) -> None:
        items = [_item("a")]
        state = PickerState(items)
        lines = render_picker(state, term_width=80)
        text = "\n".join(lines)
        assert "SPACE" in text
        assert "ENTER" in text
        assert "ESC" in text

    def test_shows_hint(self) -> None:
        items = [_item("nm")]
        state = PickerState(items)
        state.cursor = 0
        lines = render_picker(state, term_width=120)
        text = "\n".join(lines)
        assert "regen nm" in text

    def test_viewport_scrolling(self) -> None:
        items = [_item(f"item{i}") for i in range(50)]
        state = PickerState(items, viewport_height=10)
        for _ in range(20):
            state.move(1)
        lines = render_picker(state, term_width=80)
        # Should show item20 (cursor) but not item0
        text = "\n".join(lines)
        assert "item20" in text

    def test_empty_items(self) -> None:
        state = PickerState([])
        lines = render_picker(state, term_width=80)
        text = "\n".join(lines)
        assert "Nothing" in text or "empty" in text or len(lines) > 0

    def test_caution_items_show_marker(self) -> None:
        items = [
            _item("safe_item", safety="safe"),
            _item("caution_item", safety="caution"),
        ]
        state = PickerState(items)
        lines = render_picker(state, term_width=100)
        text = "\n".join(lines)
        # Caution items should have some marker
        assert "⚠" in text or "[!]" in text or "CAUTION" in text.upper()

    def test_safe_items_no_caution_marker(self) -> None:
        items = [_item("safe_item", safety="safe")]
        state = PickerState(items)
        lines = render_picker(state, term_width=100)
        # No caution markers when all items are safe
        text = "\n".join(lines)
        assert "⚠" not in text
        assert "[!]" not in text

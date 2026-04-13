"""Tests for picker item helpers (the interactive part is delegated to questionary)."""

from __future__ import annotations

from pathlib import Path

from questionary import Choice, Separator

from disk_free.picker import PickerItem, _build_choices, _format_choice_title


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
        item = _item("node_modules", size=5000, group="Caches", safety="safe")
        assert item.label == "node_modules"
        assert item.size_bytes == 5000
        assert item.group == "Caches"
        assert item.hint == "regen node_modules"
        assert item.safety == "safe"

    def test_default_safety_is_safe(self) -> None:
        item = PickerItem(
            path=Path("/tmp/x"), size_bytes=0, label="x",
            description="", hint="",
        )
        assert item.safety == "safe"


def _title_text(formatted_text) -> str:  # type: ignore[no-untyped-def]
    """Extract the plain-text content of a FormattedText title."""
    return "".join(segment for _, segment in formatted_text)


class TestFormatChoiceTitle:
    def test_includes_size_label_and_description(self) -> None:
        item = _item("node_modules", size=1_000_000_000)
        text = _title_text(_format_choice_title(item))
        assert "node_modules" in text
        assert "node_modules desc" in text
        assert "regen node_modules" in text

    def test_caution_has_warning_marker(self) -> None:
        item = _item("system-images", safety="caution")
        text = _title_text(_format_choice_title(item))
        assert "⚠" in text

    def test_safe_has_no_warning_marker(self) -> None:
        item = _item("node_modules", safety="safe")
        text = _title_text(_format_choice_title(item))
        assert "⚠" not in text

    def test_caution_applies_caution_style_class(self) -> None:
        item = _item("system-images", safety="caution")
        formatted = _format_choice_title(item)
        styles = [cls for cls, _ in formatted]
        assert any("caution" in cls for cls in styles)

    def test_size_class_varies_by_magnitude(self) -> None:
        big = _format_choice_title(_item("x", size=2 * 1024**3))
        med = _format_choice_title(_item("y", size=500 * 1024**2))
        sm = _format_choice_title(_item("z", size=10 * 1024**2))
        big_styles = [cls for cls, _ in big]
        med_styles = [cls for cls, _ in med]
        sm_styles = [cls for cls, _ in sm]
        assert "class:item-size-big" in big_styles
        assert "class:item-size-med" in med_styles
        assert "class:item-size-sm" in sm_styles


class TestBuildChoices:
    def test_returns_choice_per_item(self) -> None:
        items = [_item("a"), _item("b"), _item("c")]
        choices = _build_choices(items)
        picks = [c for c in choices if isinstance(c, Choice)]
        assert len(picks) == 3

    def test_inserts_separator_when_group_changes(self) -> None:
        items = [
            _item("a", group="First"),
            _item("b", group="First"),
            _item("c", group="Second"),
        ]
        choices = _build_choices(items)
        separators = [c for c in choices if isinstance(c, Separator)]
        assert len(separators) == 2

    def test_caution_group_header_mentions_caution(self) -> None:
        items = [_item("x", group="Android SDK", safety="caution")]
        choices = _build_choices(items)
        sep_texts = [
            _title_text(c.title) for c in choices if isinstance(c, Separator)
        ]
        assert any("CAUTION" in t or "⚠" in t for t in sep_texts)

    def test_safe_group_header_no_caution_label(self) -> None:
        items = [_item("x", group="Caches", safety="safe")]
        choices = _build_choices(items)
        sep_texts = [
            _title_text(c.title) for c in choices if isinstance(c, Separator)
        ]
        for t in sep_texts:
            assert "CAUTION" not in t

    def test_choices_preserve_item_order(self) -> None:
        items = [_item("a"), _item("b"), _item("c")]
        choices = _build_choices(items)
        picks = [c for c in choices if isinstance(c, Choice)]
        # Choice.value is the index we assigned
        assert [c.value for c in picks] == [0, 1, 2]

    def test_items_without_group_still_appear(self) -> None:
        items = [_item("a", group=""), _item("b", group="")]
        choices = _build_choices(items)
        picks = [c for c in choices if isinstance(c, Choice)]
        assert len(picks) == 2

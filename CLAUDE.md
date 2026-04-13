# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Dev commands

```bash
# Setup (editable install with test deps)
python3 -m venv .venv
.venv/bin/pip install -e . pytest

# Run all tests
.venv/bin/pytest

# Run a single test file / class / function
.venv/bin/pytest tests/test_picker.py
.venv/bin/pytest tests/test_picker.py::TestBuildChoices
.venv/bin/pytest tests/test_picker.py::TestBuildChoices::test_caution_group_header_mentions_caution

# Run the tool (after install)
.venv/bin/disk_free inspect <path>
.venv/bin/disk_free system
```

Note: the `README.md` is stale — it describes an older `ls` subcommand that no longer exists. The current CLI exposes only `inspect` and `system`.

## Architecture

This is a Python stdlib-first CLI (one dependency: `questionary` for the interactive picker). The code splits into **pure scanning/formatting** and **terminal UI**, kept decoupled so the scanning logic is unit-testable without a TTY.

### Two commands, one picker

- `disk_free inspect <path>` — shows a tree overview of where space lives under `<path>` (via `inspect.deep_scan`), then finds removable build artifacts (`artifacts.find_artifacts`) and hands them to the interactive picker for per-item cleanup.
- `disk_free system` — scans a curated list of macOS system targets (`system.DEFAULT_CATEGORIES`) and hands them to the same picker.

Both commands produce `PickerItem`s and funnel through `picker.run_picker`, which wraps `questionary.checkbox`. The deletion flow after the picker is shared (`cli._remove_items`).

### Module responsibilities

- `scanner.py` — `dir_size()` walks files and sums `st_size`; `scan_subdirs()` returns immediate children with sizes. Symlinks are not followed (guards against Steam.app-style self-referential bundles).
- `inspect.py` — `deep_scan()` returns a `TreeEntry` tree, auto-drilling into children above a `min_bytes` threshold up to `depth` levels. Also skips symlinks.
- `artifacts.py` — `ARTIFACT_RULES` lists directory names considered removable (`node_modules`, `.next`, `dist`, `.venv`, `__pycache__`, etc.). `find_artifacts()` walks a tree, emits an `Artifact` for each match, and does **not descend into artifact dirs** (so a `node_modules` nested inside another is counted once).
- `system.py` — `DEFAULT_CATEGORIES` is a static list of `Category` → `SafeTarget` paths with descriptions, regeneration hints, and a `safety` field (`"safe"` or `"caution"`). `scan_categories()` returns only targets that exist with size > 0. **Add new cleanup targets here.** Categories currently span: Developer (Xcode), Caches (macOS app caches + ShipIt updaters), Dev Tool Caches (npm/uv/yarn/bun/puppeteer/etc.), Logs, Android SDK (caution), App VMs & User Data (caution).
- `picker.py` — wraps `questionary.checkbox`. `PickerItem` is the shared type; `_build_choices()` converts a list of items into `Choice` + `Separator` entries (group headers), colored via `FormattedText` tuples and a `Style` defined in `_PICKER_STYLE`. Caution items show a `⚠` marker + yellow text; size is colored by magnitude (red ≥1G, yellow ≥100M, green otherwise).
- `formatter.py` — pure functions: `human_size()`, `format_tree()`, etc. Imports are guarded with `TYPE_CHECKING` to avoid circular deps.
- `progress.py` — stderr-only progress lines (scanning dir, remove progress bar). Uses ANSI escapes directly; works alongside `questionary` because they write to different streams.
- `cli.py` — argparse wiring. Converts domain objects (`Artifact`, `CategoryResult`) into `PickerItem`s and orchestrates the scan → picker → remove flow.

### Conventions that matter

- **Dataclasses are `frozen=True`** by default. The picker's `PickerState` was the exception and has since been removed (questionary owns state now). When adding new domain types, follow the frozen pattern.
- **Safety flags propagate end-to-end**: `SafeTarget.safety` → `PickerItem.safety` → picker rendering. When adding new targets, set `safety="caution"` for anything that's not a pure regenerable cache (user data, VMs, multi-version toolchains, IDE extensions).
- **Scans skip symlinks and swallow `PermissionError`/`OSError`** so one bad directory (Steam's bundle, a permission-blocked iCloud dir) doesn't abort the whole scan.
- **Tests mock `disk_free.cli.run_picker`** rather than trying to drive the TTY. Interactive behavior is delegated to questionary and assumed-correct; we test the plumbing around it.

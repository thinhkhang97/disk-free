# disk_free

A developer-focused Mac disk cleaner: find build artifacts, system caches, and stale files — with restore hints and caution warnings before touching anything.

> **Note:** This project is no longer actively developed. See [DECISION.md](./DECISION.md) for why.

## Commands

```bash
# Scan a project directory for removable artifacts (node_modules, .venv, Pods, etc.)
disk_free inspect ~/Projects/my-app

# Scan macOS system directories (Xcode, Android SDK, app caches, dev tool caches)
disk_free system

# Find large files untouched for 90+ days
disk_free stale ~/Projects
```

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Project structure

```
src/disk_free/
├── cli.py          # Argparse entry point + orchestration
├── scanner.py      # Directory walking and size computation
├── inspect.py      # Deep tree scan
├── artifacts.py    # Build artifact detection (ARTIFACT_RULES)
├── system.py       # Curated macOS system targets (DEFAULT_CATEGORIES)
├── stale.py        # Age-aware large file discovery
├── picker.py       # Interactive multi-select UI (questionary)
├── formatter.py    # Human-readable sizes and tree formatting
└── progress.py     # Stderr progress indicators
```

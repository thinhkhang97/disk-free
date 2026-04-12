# disk_free

A CLI tool to list subdirectory sizes at a glance.

## Installation

```bash
uv venv && uv pip install -e .
```

## Usage

```bash
# List subdirectory sizes (sorted largest first)
disk_free ls ~/Projects/Products

# Defaults to current directory
disk_free ls

# Help
disk_free --help
```

### Example output

```
 2.2G  infina-pfa
 1.8G  infina-partner-sdk
 1.3G  infina-pfa-be
 992M  infina-ai-backend
 827M  b2c-infina-integration-services
 312M  infina-ai-dash
 230M  cloud-quiz
80.1K  agent-config
─────  ──────
 7.7G  total (8 dirs)
```

## Project structure

```
src/disk_free/
├── cli.py          # Argparse entry point
├── scanner.py      # Directory walking and size computation
└── formatter.py    # Human-readable sizes and table formatting
```

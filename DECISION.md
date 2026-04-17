# Why I Stopped Building disk_free

> A record of the research and reasoning that led to this decision.
> Written April 2026.

---

## The Original Pain Point

As a fullstack developer switching between stacks (web, iOS, Android, backend), I accumulate junk silently:

- `node_modules` from projects I haven't touched in months
- Xcode `DerivedData`, iOS simulators, CocoaPods from a mobile sprint long past
- Android emulator images and NDK from a role I've since moved out of
- macOS reporting "120GB System Data" with no explanation of what it is

Existing tools were either too aggressive (removed Chrome caches → logged me out of all accounts), too broad (showed everything, cleaned nothing intelligently), or too narrow (only one ecosystem).

The goal was a tool that:
- Discovers "covered in dust" items across all dev stacks
- Shows exactly what each item is and **how to restore it** if needed
- Flags items it's not sure about with a clear **caution warning**
- Lets me pick manually — safe, not automatic

---

## What disk_free Built

Three commands, each with a distinct philosophy:

| Command | What it does |
|---|---|
| `inspect <path>` | Tree overview of a directory + finds build artifacts (node_modules, .venv, Pods, etc.) |
| `system` | Scans curated macOS paths — Xcode, Android SDK, app caches, logs, dev tool caches |
| `stale <path>` | Heuristic: finds large files untouched ≥N days, ranked by `size × age` |

Unique ideas that went into it:
- **Restore hints** on every item ("how to regenerate after removing")
- **`safe` vs `caution` classification** — explicit per-item warnings before touching anything
- **Age-aware scoring** for the stale finder — not just "is it old?" but ranked by how much space × how long untouched

---

## What Already Exists

During a research session in April 2026, I found these tools cover the same job:

| Tool | What it does well |
|---|---|
| **[Mole](https://github.com/tw93/Mole)** (`brew install mole`) | Comprehensive: purge artifacts, analyze disk, clean caches, smart uninstall, live status dashboard |
| **`npx npkill`** | Interactive picker for all `node_modules` on your machine — fast, zero-install |
| **DaisyDisk** (~$10) | Visual disk map — best for "where is my 120GB?" |
| **`brew cleanup`** | Removes old Homebrew versions in one command |
| **Xcode → Settings → Platforms** | Built-in UI to delete old simulators safely |

---

## Why Mole Wins

Mole (`mo`) does everything disk_free was building toward, and more:

- `mo purge` — finds project artifacts across all your repos, age-aware (marks projects <7 days as unselected by default), interactive picker
- `mo analyze` — visual disk explorer with navigation, shows directory ages, moves to Trash via Finder (safe)
- `mo clean` — system caches, logs, browser leftovers, developer tool caches
- `mo uninstall` — removes apps + all 20+ hidden remnants
- `mo status` — live CPU/memory/disk dashboard
- `--dry-run` on every destructive command
- Raycast/Alfred integration
- `brew install mole` — zero friction

It's open-source, MIT licensed, actively maintained, and free.

---

## What disk_free Got Right (That Mole Still Lacks)

To be fair, disk_free identified two genuine gaps in the ecosystem:

1. **Restore hints** — no existing tool tells you *how to regenerate* what you're about to delete. disk_free showed "run `npm install`" or "run `pod install`" next to every item.
2. **Explicit caution/safe classification** — a named, visible signal per item distinguishing "purely regenerable cache" from "takes 2GB to re-download" or "contains user data."

These are real UX improvements. But they are **PR-sized contributions to Mole**, not a full tool's worth of differentiation. Two focused PRs to Mole's `mo purge` would reach more developers than maintaining a separate tool.

---

## The Conclusion

Most developers will install Mole. It wins on breadth, distribution, and daily usability.

disk_free as a competing product doesn't make sense to build further.

**What this project actually was:** a well-executed learning exercise. It produced clean Python architecture — frozen dataclasses, decoupled scanner/formatter/picker layers, testable pure functions, a real interactive TUI via questionary — and surfaced genuine product insight (restore hints, caution classification) that would have value if contributed upstream.

The code is good. The market timing was bad. Mole got there first and got there broadly.

---

## What To Do With the Insight

If the restore hints + caution classification idea still feels worth pursuing:

- Open a GitHub issue on [tw93/Mole](https://github.com/tw93/Mole) proposing the feature
- The `mo purge` interactive picker is the right place to add restore hints per artifact type
- Caution classification could gate items like Android system images or nvm versions with a visible warning

Otherwise: leave this repo as-is, reference it as a portfolio piece, and use Mole.

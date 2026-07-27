---
paths:
  - "docs/ROADMAP.md"
---

# ROADMAP

`docs/ROADMAP.md` is the single source of truth for milestones.

| | ROADMAP | Devlog |
|---|---|---|
| update mode | overwrite, always current | append-only |
| records | what we intend to do, where we are | what happened, and why |
| on conflict | current state wins | historical context |

The archive repo's ROADMAP is frozen and kept for historical reference only.
Where the two differ, this one wins.

## When to update

1. milestone completed → mark ✅ and update the TL;DR
2. milestone structure changed — added, split, reordered → Decisions Log plus
   the affected milestone
3. backlog changed → update the backlog section
4. `進行當日總結` triggered → reconcile the ROADMAP against the day's devlog

## Keeping it from bloating

- completed milestones keep one line and a completion date; detail lives in
  the devlog
- the changelog keeps the last 10–15 entries; git history carries the rest
- the Decisions Log has a deliberately high bar: only decisions that change
  milestone structure or ordering

## Committing

ROADMAP changes go in their own commit, separate from code changes — it keeps
planning traceable independently of implementation. Writing needs Stan's
explicit approval.

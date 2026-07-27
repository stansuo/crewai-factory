---
paths:
  - "docs/devlog/**"
---

# Devlog

Devlogs are the baseline for AI collaboration and future handover: what was
done, why, what the risks are, how it was verified, what comes next.

## Template

`docs/devlog/_DEVLOG_TEMPLATE.md` is the only source. Read it before writing
and fill in its sections. Sections that don't apply get `N/A`, but keep the
numbering. If the template can't be read, say so and fall back to the most
recent known format.

## Filenames

`docs/devlog/YYYYMMDDNN_short-slug.md`

- `NN` is that day's sequence number, starting at `01`
- `short-slug` is lowercase English with hyphens
- **A session spanning days, or resumed after an interruption, keeps the
  earlier date.** A session boundary tracks the actual line of thinking better
  than the calendar does. Before starting, check whether this is a continuation
  of an existing devlog — if so, append to it rather than opening a new file.

Example: `2026042801_init-celery-worker.md`

## What to record

Major architectural or directional decisions; components added or removed;
significant problems or risks discovered; verifiable milestones reached.

Quality bar:

- decisions record **why**, not only what
- milestones must be verifiable, and state the verification method
- the handover snapshot assumes a reader who has never seen the project
- anything uncertain is labelled as inference

## Prompting Stan

Don't nag about writing devlogs — it interrupts the work. Emit a single
`[CAUTION]` line only for:

1. high-risk decisions — security, secrets, public exposure, destructive ops
2. architecture-level shifts affecting several downstream components
3. decisions that contradict an earlier devlog
4. milestone or backlog changes, prompting a ROADMAP check at day's end

Once per topic is enough.

    [CAUTION] 這個決策建議記下來，因為它會影響後續所有 worker 的網路架構。

## Triggers

| Command | Scope | Output |
|---|---|---|
| `整理 devlog` | chat start, or last trigger, to now | ad-hoc draft — template §1–4, 6, 7 |
| `進行當日總結` | the whole day | full template plus ROADMAP reconciliation |

`進行當日總結` additionally produces learning notes, an AI handover snapshot
that can be pasted straight into a fresh session, and an explicit ROADMAP check
covering milestone status, backlog changes, and Decisions Log candidates —
each with a stated conclusion of "needs update" or "no change". Earlier
`[CAUTION]` lines are the anchors worth revisiting.

Drafts only. Writing to the repo needs Stan's explicit approval.

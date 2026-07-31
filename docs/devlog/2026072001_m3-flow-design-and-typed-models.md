# 2026-07-20: Start M3 — settle the Flow design and land the typed models

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: In Progress
**Related commits / PRs**: branch `feat/m3-flow-skeleton` — `54d83eb` (format target), `e23192d` (typed models), `cb5f78d` (phony registration)

---

## TL;DR

M3 development started. The full CrewAI Flow architecture was designed and settled before any code: a five-node flow (`generate_topic` → `write_draft` → `edit_draft` → `route_verdict` → `save_output` / `handle_failure`) with a single router branching on a typed editor verdict, and a retry loop wired via `or_`. Three design decisions were locked in: routers are business-decision points only (technical failures fail fast via exceptions); on retry-cap exhaustion the best-scoring attempt is saved and marked FAILED (the attempt history doubles as raw data for M5+ performance tracking); the existing 3-task Crew splits into three single-task crews wrapped in Flow steps, reusing all existing agents. The first implementation slice landed on `feat/m3-flow-skeleton`: `EditorVerdict` (in `tasks.py`) plus `Attempt` and `ContentState` (in the new `flow.py`), all Pydantic models passing `make ci`. The sequential pipeline is untouched and still operational. Next: the `ContentFlow` class itself.

## 1. Decisions

### Decision 1: One router only — routers branch on business outcomes, exceptions handle technical failures
- **What**: The flow has exactly one `@router`, placed after the editor step, branching on the typed verdict plus the retry count. Technical failures (LLM backend down, I/O errors, `output_pydantic` parse failures) are not routed; they raise and fail the run (fail fast).
- **Why**: A router is a business-decision point ("does this draft pass?"), and the pipeline has exactly one such decision. Per-node error routing is a cross-cutting concern that belongs to the language's exception mechanism; encoding it in the flow topology would double the node count while duplicating identical "is it broken?" logic everywhere — reinventing try/except as a flowchart. A failed run is retried by the scheduler (M4: systemd timer), not inside the flow.
- **Alternatives considered**: A router (or error branch) per node — rejected as an anti-pattern for the reasons above.
- **Risks & mitigations**: A transient parse failure kills an otherwise healthy run → accepted for M3; revisit with a bounded retry only if real runs show it happening frequently (see Open Questions).

### Decision 2: On retry-cap exhaustion, save the best-scoring attempt marked FAILED
- **What**: When all attempts fail, `handle_failure` persists the highest-scoring draft with a FAILED marker instead of discarding the run or keeping only the last draft.
- **Why**: The marginal cost is one list in the flow state; the return is (a) the best artifact survives even on failure and (b) the full retry trajectory (draft, score, feedback per cycle) is preserved — exactly the raw data M5+ performance tracking needs (pass rates, retry distributions, whether feedback improves scores across cycles).
- **Alternatives considered**: Save last attempt only (loses information for zero savings); save nothing and exit non-zero (strictest, but discards work).
- **Risks & mitigations**: None significant; state size is bounded by the retry cap.

### Decision 3: Split the single 3-task Crew into three single-task crews inside Flow steps
- **What**: Each Flow step runs its own single-agent, single-task Crew, reusing `build_agents` unchanged. The router must sit between the writer and the terminal steps, so the tasks cannot stay bound in one `Crew`.
- **Why**: Minimal diff — `agents.py` and `persona.py` are untouched; changes concentrate in `tasks.py` (split builders, add the typed verdict) and the new `flow.py`. The sequential path remains intact until the Flow replaces it, keeping every intermediate commit shippable and rollbackable.
- **Alternatives considered**: Direct LLM calls per step (drops the agent/persona machinery M2 built); hierarchical process (already rejected in the 2026-04-28 decision, reconfirmed).
- **Risks & mitigations**: Slight per-step Crew overhead → negligible at this scale.

### Decision 4: State model shape — no derived counters, total-attempts semantics
- **What**: `ContentState` stores no separate cycle counter; the cycle count is `len(attempts)` (single source of truth — derived values are not stored). The cap field is named `max_attempts` with "total attempts" semantics (renamed from `max_retries` during review to eliminate off-by-one ambiguity in the router condition).
- **Why**: A stored counter alongside the list is two sources of truth that can silently drift apart. Name/semantics alignment makes the router condition read literally: `len(attempts) >= max_attempts`.
- **Alternatives considered**: Keep `max_retries` with "after the initial attempt" semantics — workable but requires a `+ 1` in the condition; rejected for readability.
- **Risks & mitigations**: `Attempt.cycle` is technically derivable from the list index but kept deliberately — it freezes at write time (cannot drift) and makes logs and saved records self-describing.

## 2. System Changes

- `[Add]` **`EditorVerdict`** (`tasks.py`): Pydantic schema for the editor's structured verdict (`score` 0–100, `passed`, `feedback`, `final_post`). Will back `output_pydantic` on the editor task; field descriptions are written as LLM-facing format instructions since CrewAI feeds the schema to the model. The existing string-format `build_tasks` is untouched — the sequential pipeline still runs.
- `[Add]` **`flow.py`** (`Attempt`, `ContentState`): the M3 module. `Attempt` records one write-edit cycle (cycle, score, content, feedback); `ContentState` is the shared flow state (topic, post, optional verdict, `max_attempts`, `attempts` list via `default_factory`). The `ContentFlow` class will live here next.
- `[Modify]` **`Makefile`**: new `format` target (`ruff format` + `ruff check --fix`) as the fix-side counterpart to the check-only `lint`; `format` and the previously unregistered `test-cov` added to `.PHONY`.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | `flow.py` lacks a module docstring (style inconsistency with other modules) | Open | Add when writing the `ContentFlow` class |
| Low | `output_pydantic` parse failures fail the whole run (Decision 1) | Open | Acceptable for M3; revisit with evidence from real runs |

## 4. Milestones

- [x] **M3 flow architecture designed and settled** (topology, loop wiring via `or_`, failure semantics, state shape)
  - **Verification**: Decisions 1–4 above; design maps one-to-one onto the M3 definition of done in the roadmap.
  - **Status**: Verified
- [x] **Typed models landed on `feat/m3-flow-skeleton`**
  - **Verification**: `make ci` green locally (ruff + mypy strict + pytest); remote fetch confirms `tasks.py`, `flow.py`, and `Makefile` contents on the branch match the reviewed versions.
  - **Status**: Verified
- [ ] **M3 definition of done (5 items)** — in progress; none complete yet.

## 5. Learning Notes

### Commands / Code
- Command: `git switch -c <branch>` (after `git checkout main && git pull`)
  - Purpose: create a feature branch from the up-to-date main, not a stale local one.
  - Verification: `git status` shows the new branch with a clean tree.
  - Rollback: `git switch main && git branch -D <branch>` (nothing pushed yet).
- Command: `ruff format --check` vs `ruff format` / `ruff check --fix`
  - Purpose: check-vs-fix separation — `lint` is read-only (CI-safe, no side effects), `format` mutates the working tree.
  - **Lesson**: "Would reformat" + make Error 1 from `make lint` is the check mode working as designed, not a failure of the tool. The same `--check` / `--fix` / `--dry-run` pattern appears across the whole tooling ecosystem.
- Command: `git add -A` before running auto-formatters
  - Purpose: use the staging area as a lightweight snapshot — afterwards, bare `git diff` shows only the tool's changes, `git diff --staged` shows only yours.
  - **Lesson**: better yet, commit manual work first and let tool churn be its own commit — snapshots make "what did the tool do" always answerable. (Learned the hard way: a mixed diff is unrecoverable after the fact.)
- Concept: long-string E501 fixes
  - **Lesson**: break `Field(...)` arguments one-per-line first; if still long, use implicit string concatenation inside parentheses (adjacent string literals auto-join — mind the missing spaces at the seams). Avoid backslash continuation, `# noqa`, or raising the line-length limit.

### Concepts / Architecture
- Concept: **Crew (sequential) vs Flow**
  - One-line explanation: a sequential Crew is a fixed conveyor belt (context flows one way, no return station); a Flow is an event-driven graph where methods fire on events and share a typed state.
  - Role in this project: explains structurally why an editor FAIL currently becomes the final output — and why M3 is an architecture change, not a patch.
- Concept: **`@start` / `@listen` / `@router` + `or_` loop wiring**
  - One-line explanation: `@router` returns a route-name string; the retry loop forms because `write_draft` listens via `or_(generate_topic, "retry")` — two trigger sources, one node.
  - Role in this project: the core mechanism of M3's retry-until-pass.
- Concept: **Routers are for business decisions; exceptions are for failures**
  - One-line explanation: identical "is it broken?" checks at every node are a cross-cutting concern — that signal means use the language mechanism (exception propagation), not topology.
  - Role in this project: kept the flow at five nodes instead of nine-plus (Decision 1).
- Concept: **Mutable default arguments and `default_factory`**
  - One-line explanation: defaults are created once at definition time, so a `= []` default is shared across calls/instances; `default_factory=list` stores the recipe, not the basket, producing a fresh list per instance.
  - Role in this project: `ContentState.attempts`; also a portable habit — dataclasses reject `= []` outright, and Pydantic's deep-copy rescue is framework-specific.
- Concept: **Single source of truth in state design**
  - One-line explanation: don't store what you can derive — a stored counter next to the list it counts will eventually drift.
  - Role in this project: Decision 4; also the reasoning template for judging which redundancy is acceptable (`Attempt.cycle` freezes at write time, so it cannot drift).
- Concept: **Makefile basics**
  - One-line explanation: targets + TAB-indented recipes; `.PHONY` declares targets that aren't files so a same-named file can't shadow them.
  - Role in this project: added the `format` target and fixed the phony registration.

## 6. Next Steps

- [ ] **`ContentFlow` class in `flow.py`**: `@start` topic step, `@listen(or_(...))` write step with feedback injection on retries, editor step with `output_pydantic=EditorVerdict`, `@router` on the verdict + `len(attempts)`, terminal save/failure steps
- [ ] Split `build_tasks` into per-step task builders in `tasks.py`; add `output_pydantic` to the editor task
- [ ] Rewire `crew.py` `run()` to kick off the Flow (keep `RunResult` contract for the CLI)
- [ ] Integration tests with mocked Ollama covering pass-first-try, retry-then-pass, and cap-exhaustion paths
- [ ] `make demo` visibility: verbose log shows retry count (M3 DoD item 5)
- [ ] README polish in the PR-final commit: flip the M3 mermaid FAIL edge from "lands in M3" to the real loop, update the M3 status row, add `make format` to the Development section

## 7. Open Questions

- Should `output_pydantic` parse failures get one bounded retry instead of failing the run? Deferred: fail fast until real-run evidence shows the failure rate matters.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-20
Latest progress:
  - Current phase: M3 (CrewAI Flow) in progress on branch feat/m3-flow-skeleton.
  - Completed: flow architecture designed and settled (5 nodes, single router,
    or_-wired retry loop, fail-fast for technical errors, best-attempt-on-failure);
    typed models landed and remote-verified: EditorVerdict (tasks.py),
    Attempt + ContentState (new flow.py); Makefile format target + .PHONY fix.
  - In progress: ContentFlow class is the next thing to write; no flow code exists yet.

Current architecture summary:
  - Python 3.12 + CrewAI 1.15.2. The sequential pipeline (strategist → writer →
    editor) is still the active code path and untouched; M3 models sit beside it.
  - Settled M3 design: generate_topic (@start) → write_draft
    (@listen(or_(generate_topic, "retry")), injects verdict.feedback on retries)
    → edit_draft (@listen, output_pydantic=EditorVerdict) → route_verdict
    (@router: passed → "save"; not passed and len(attempts) < max_attempts →
    "retry"; else → "failed") → save_output / handle_failure (saves the
    best-scoring attempt marked FAILED).
  - ContentState: topic, post, verdict (EditorVerdict | None), max_attempts
    (default 3, total-attempts semantics), attempts (list[Attempt],
    default_factory). Cycle count is len(attempts) — no derived counters.
  - Each flow step runs a single-agent single-task Crew reusing build_agents;
    agents.py / persona.py unchanged.

Next steps:
  - Write ContentFlow in flow.py per the settled design; split build_tasks into
    per-step builders; rewire crew.py run() keeping the RunResult contract;
    integration tests (mocked Ollama) for pass / retry-pass / cap-exhaustion;
    make demo shows retry count.

For AI to be aware of:
  - This repo is PUBLIC; English-only engineering layer; never reference
    pre-public devlog IDs in public docs.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads.
  - Collaboration mode: Stan writes code with guided scaffolding and reviews;
    Claude teaches, reviews, and verifies against the remote (fetch after
    every push — tool success messages are not proof).
  - Technical failures fail fast (Decision 1, 2026-07-20); do not re-propose
    per-node error routing. Best-attempt-on-failure is settled (Decision 2).
  - OLLAMA_MODEL default stays a cloud model (decision 2026-07-16);
    do not re-propose switching to a local default.
  - Unresolved deployment security issues go to private notes (archive repo),
    never the public repo; currently zero open items.
```

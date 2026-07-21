# 2026-07-21: Build ContentFlow nodes and move the quality gate into config

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: In Progress
**Related commits / PRs**: `feat/m3-flow-skeleton` (commit TBD)

---

## TL;DR
Wrote the first three `ContentFlow` nodes (`generate_topic`, `write_draft`,
`edit_draft`) on `feat/m3-flow-skeleton`, wiring data through `self.state` and
producing a structured editor verdict via `output_pydantic`. Decided to enforce
the pass/fail threshold in code rather than in the editor prompt: added
`Settings.quality_threshold` and removed `EditorVerdict.passed`, so the gate
becomes `score >= quality_threshold` — deterministic and testable. The router
and terminal nodes are still stubs, so there is no end-to-end run yet.

## 1. Decisions

### Decision 1: Enforce the quality threshold in code, not in the editor prompt
- **What**: The editor agent now only scores the post and writes feedback. The
  pass decision moves into code as `score >= Settings.quality_threshold`
  (default 85). `EditorVerdict.passed` is removed; `Settings.quality_threshold`
  is added and is env-overridable.
- **Why**: (1) Testability — M3 DoD #4 requires integration tests over
  pass / retry-pass / cap-exhaustion; with an LLM-decided `passed`, a mocked
  score does not deterministically map to a branch, so tests would be flaky.
  A code-side comparison makes the branch a pure function of the score.
  (2) Single source of truth — the threshold lives in config, not scattered in
  a prompt string, and can be tuned without touching prompts. (3) Removes a
  bug class — the editor can no longer report `score=84, passed=True`.
- **Alternatives considered**: Keep the LLM-decided `passed` — rejected
  (non-deterministic, flaky tests, two competing pass signals). Keep `passed`
  as a field but override it in code — rejected (a dead/confusing field; a
  reader cannot tell which signal wins).
- **Risks & mitigations**: The editor still influences the outcome through the
  score it assigns — accepted, that is the intended qualitative judgment. The
  threshold value (85) is a guess — mitigated by making it a config value so it
  can be tuned once real-run pass-rate data exists.

## 2. System Changes
- `[Add]` `flow.ContentFlow`: `generate_topic` (`@start`), `write_draft`
  (`@listen(or_(generate_topic, "retry"))`), `edit_draft` (`@listen`). Each node
  runs a single-agent Crew reusing `build_agents`; data passes through
  `self.state`. `edit_draft` uses `output_pydantic=EditorVerdict` and appends one
  `Attempt` per cycle.
- `[Add]` `config.Settings.quality_threshold` (default 85, env-overridable).
- `[Modify]` `tasks.EditorVerdict`: removed `passed`; the field is now derived
  in code.
- `[Modify]` `flow.edit_draft`: inject the threshold into the editor prompt;
  structured `expected_output` (score / feedback / final_post).
- `[Modify]` `.env.example`: add `QUALITY_THRESHOLD`.
- The legacy sequential path (`build_tasks`, `crew.py`) is untouched and still
  active; it does not use `EditorVerdict`, so removing `passed` does not affect
  it.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | `flow.py` is mid-build: router and terminal nodes are stubs (`...`) | In Progress | Feature-branch WIP; not merged until DoD is met and CI `quality` passes |
| Low | `final_post` semantics are now ambiguous — the editor no longer owns the pass decision | Open | Resolve when writing `save_post` (use `final_post` vs `self.state.post`) |

## 4. Milestones

- [ ] M3 DoD #3 — editor verdict uses structured output; router branches on typed fields
  - **Verification**: `edit_draft` uses `output_pydantic=EditorVerdict` and reads `result.pydantic`; `route_verdict` will branch on `verdict.score` (typed), never free text.
  - **Status**: Pending (code written for `edit_draft`; router not yet written; no end-to-end run)
- [ ] M3 DoD #1 — `@start` / `@listen` / `@router` replace `Process.sequential`
  - **Verification**: `ContentFlow` fully wired and `kickoff()` runs the loop.
  - **Status**: Pending (3 of ~6 nodes written)

## 5. Learning Notes

### Concepts / Architecture

- Concept: **config-schema-with-env-override** (`pydantic-settings`)
  - One-line explanation: `config.py`'s `Settings` class is the *schema*
    (field names, types, defaults, startup validation); `.env` supplies the
    *actual per-environment values*, loaded and type-coerced at startup;
    `.env.example` is the human-facing *template* committed to git.
  - Role in this project: explains why the same keys appear in `config.py` and
    `.env` without being duplication. Three layers: schema + safe defaults
    (`config.py`, in git) → fill-in template (`.env.example`, in git) → real
    values including secrets (`.env`, git-ignored). Type validation catches a
    bad env value at startup rather than mid-run; defaults let the app run with
    no `.env`. Note `extra="ignore"` currently drops the `X_*` keys from
    `.env.example` — those `Settings` fields will be added in M4 when the X
    client is built.

- Concept: **Flow data flow vs control flow**
  - One-line explanation: nodes pass data through `self.state`; the signal that
    triggers a `@listen` is the upstream method *finishing*, not its return
    value.
  - Role in this project: every node returns `None`; only `@router` returns a
    string, and that string is a routing label (a channel name), not data.

- Concept: **`output_pydantic` → `result.pydantic`**
  - One-line explanation: a `Task` with `output_pydantic=Model` yields a typed
    object on `result.pydantic` (versus free text on `result.raw`).
  - Role in this project: lets the router branch on typed fields, satisfying
    DoD #3.

- Concept: **guard the container before the attribute**
  - One-line explanation: `if self.state.verdict` checks the object exists;
    `if self.state.verdict.feedback` dereferences `None` on the first cycle and
    raises `AttributeError`.
  - Role in this project: the first `write_draft` pass has `verdict is None`, so
    feedback injection must guard `verdict` first (and `and` short-circuits for
    the two-level check).

## 6. Next Steps
- [ ] `route_verdict` (`@router`): compute `passed = verdict.score >= settings.quality_threshold`; return `"save"` / `"retry"` / `"failed"` using `len(attempts)` vs `max_attempts`.
- [ ] `save_post` (`@listen("save")`): persist the approved text; resolve `final_post` vs `self.state.post`.
- [ ] `handle_failure` (`@listen("failed")`): save the best-scoring attempt, tagged failed.
- [ ] (optional) split `build_tasks` into per-step builders.
- [ ] rewire `crew.py` `run()` to kick off the Flow; keep the `RunResult` contract.
- [ ] integration tests (mocked Ollama): pass-first-try, retry-then-pass, cap-exhaustion.
- [ ] `make demo`: verbose log shows the retry count (DoD #5).

## 7. Open Questions
- `final_post`: does the editor still populate it, or does `save_post` use
  `self.state.post`? Decide when writing `save_post`.
- `output_pydantic` parse failure currently fails fast (raises). Keep, or allow
  one bounded retry? Deferred until real-run failure-rate evidence.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-21
Latest progress:
  - Current phase: M3 (CrewAI Flow) on branch feat/m3-flow-skeleton.
  - Completed this session: ContentFlow.__init__ + generate_topic + write_draft
    + edit_draft written; data flows through self.state; edit_draft uses
    output_pydantic=EditorVerdict and records one Attempt per cycle.
  - Decision: the quality gate is now code-side. Settings.quality_threshold
    added; EditorVerdict.passed removed; gate = score >= quality_threshold,
    to be enforced in route_verdict.
  - In progress: route_verdict, save_post, handle_failure are still stubs (...).

Current architecture summary:
  - Python 3.12 + CrewAI 1.15.2. The sequential pipeline is untouched and still
    active; ContentFlow is built beside it.
  - generate_topic (@start) -> write_draft (@listen(or_(generate_topic,
    "retry"))) -> edit_draft (@listen, output_pydantic=EditorVerdict) ->
    route_verdict (@router) -> save_post ("save") / handle_failure ("failed");
    the "retry" label loops back into write_draft.
  - Each node runs a single-agent Crew reusing build_agents. Data flows only
    through self.state (ContentState: topic, post, verdict, max_attempts=3,
    attempts=list[Attempt]). Cycle count is len(attempts).
  - Pass decision is code-side: score >= Settings.quality_threshold (default 85).

Next steps:
  - Write route_verdict (compute passed from the threshold), save_post,
    handle_failure.
  - Split build_tasks; rewire crew.py run() (keep RunResult); integration tests
    (mocked Ollama) for pass / retry-pass / cap; make demo shows retry count.

For AI to be aware of:
  - Repo is PUBLIC; English-only engineering layer; never reference pre-public
    devlog IDs in public docs.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads. Confirm
    writes by re-fetching the remote, not by tool success messages.
  - Technical failures fail fast (Decision 1, 2026-07-20); best-attempt-on-
    failure on cap exhaustion (Decision 2, 2026-07-20).
  - OLLAMA_MODEL default stays a cloud model (decision 2026-07-16).
  - Unresolved deployment security issues go to private notes (archive repo);
    currently zero open items.
```

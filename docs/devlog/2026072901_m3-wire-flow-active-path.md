# 2026-07-29: Wire run() into ContentFlow, making the Flow the active pipeline

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: In Progress
**Related commits / PRs**: branch `feat/m3-flow-skeleton` — `7ecf2a4` (save_post returns content), `316155c` (terminal nodes record saved_content), `48cfca4` (wire run() into ContentFlow), `6dbd5db` (RuntimeError for invalid internal state)

---

## TL;DR
Completed M3 Stage B: `crew.py run()` now kicks off `ContentFlow` instead of the
legacy sequential `Crew`, making the Flow the **active** pipeline (M3 DoD #1).
The change hinged on one design decision carried over from the 2026-07-28
handoff — how `run()` obtains the exact text that was persisted, given that the
failure path saves the best-scoring attempt rather than the last draft. Resolved
by giving `output.save_post` a second return value (the content it actually
wrote) and a new `ContentState.saved_content` field that both terminal nodes set
from that return value; `run()` reads `saved_content` and `output_path` from
`flow.state`, fails fast if either is missing, and builds the unchanged
`RunResult`. Verified end to end with `make demo` (one-pass run, editor score 90,
saved to `output/`). Four pre-existing `ValueError` guards in `flow.py` were
reclassified to `RuntimeError` in a separate commit. Stages C (integration
tests), D (`make demo` retry count), and E (docs + PR) remain; dead-code removal
from the migration is now a backlog item.

## 1. Decisions

### Decision 1: `save_post` returns `(path, content)`; a single field carries the saved text
- **What**: `output.save_post` now returns a `tuple[Path, str]` — the file path
  plus the exact content it wrote. `ContentState` gains `saved_content: str | None`;
  both terminal nodes (`save_output`, `handle_failure`) set it from `save_post`'s
  return value, not from the text they passed in. `run()` reads
  `flow.state.saved_content` for `RunResult.content`.
- **Why**: On the failure path, `handle_failure` persists the best-scoring
  attempt (`max(attempts, key=score)`), which may differ from `state.post` (the
  last draft). Reading `state.post` in `run()` would therefore return text that
  does not match the file on disk in the failure case. Sourcing the saved text
  from the function that actually performs the write makes "what was returned"
  and "what was written" the same value by construction — the same
  single-source-of-truth reasoning that removed `final_post` on 2026-07-28. If a
  future change makes `save_post` transform content before writing,
  `saved_content` tracks the file automatically.
- **Alternatives considered**: (a) `run()` reads `state.post` — rejected: wrong
  text on the failure path. (b) Both terminal nodes overwrite `state.post` with
  the final text — rejected: overloads one field with two meanings ("current
  draft" during the loop, "final result" at the end), reopening the ambiguous-
  ownership problem that `final_post` removal had closed. (c) Terminal nodes
  write `saved_content` from the text they hold rather than from `save_post`'s
  return — rejected: equivalent today, but silently diverges the moment
  `save_post` transforms content.
- **Risks & mitigations**: Changing a shared, tested function's signature broke
  its call sites (caught by CI: `crew.py` type error, `test_output` unpacking).
  Mitigated by updating all call sites and adding an assertion in `test_output`
  that the returned content equals the input — pinning the new contract.

### Decision 2: Reclassify internal-state guards from `ValueError` to `RuntimeError`
- **What**: The four existing `raise ValueError(...)` guards in `flow.py` (no
  topic yet; editor did not return a valid `CrewOutput`; editor did not return a
  valid `EditorVerdict`; no verdict to route) become `RuntimeError`. The new
  guard in `run()` (missing `saved_content`/`output_path`) was written as
  `RuntimeError` from the start.
- **Why**: `ValueError` semantically signals a bad argument value from the
  caller; these guards instead signal "this internal state should not occur at
  this point" — which is `RuntimeError`. Reclassifying makes the project's
  convention both consistent and semantically correct rather than consistent-but-
  imprecise. Consistent with the fail-fast-on-technical-failure principle
  (2026-07-20).
- **Alternatives considered**: Keep `ValueError` for local consistency —
  rejected: consistent with an imprecise convention. Leave old guards, use
  `RuntimeError` only for new code — rejected: creates a mixed convention.
- **Risks & mitigations**: A test asserting `pytest.raises(ValueError)` would
  break; checked before committing (none did). Kept as an isolated commit so the
  reclassification is not buried inside the wiring change.

### Decision 3: Defer dead-code removal to a separate PR (backlog)
- **What**: `build_tasks` and the sequential-`Crew` helpers are now unreferenced
  by `crew.py`, but are left in place for this session. Removal is a backlog item.
- **Why**: The wiring change is landed, green, and demo-verified; removing dead
  code is subtractive cleanup that touches multiple modules and their tests
  (`test_tasks` and similar become orphaned). Bundling it into the wiring commit
  would mix two concerns and add risk at the tail of a long session.
- **Alternatives considered**: Remove in the same commit — rejected on scope
  discipline. Remove immediately in a follow-up commit today — deferred:
  better as a focused PR with its own verification.
- **Risks & mitigations**: Dead code lingering is a low, visible cost on a
  public portfolio repo; the backlog item names the exact targets so it is not
  forgotten.

## 2. System Changes
- `[Modify]` **`output.save_post`**: return type `Path` → `tuple[Path, str]`;
  the second element is the content actually written. Backward-incompatible at
  the signature level; all call sites updated.
- `[Add]` **`ContentState.saved_content`** (`str | None`): the text persisted by
  a terminal node; `None` until the flow reaches a terminal node. Parallel to the
  existing `output_path` field.
- `[Modify]` **`flow.save_output` / `flow.handle_failure`**: unpack `save_post`'s
  `(path, content)`; set both `output_path` and `saved_content` from the return
  value.
- `[Modify]` **`crew.run()`**: kick off `ContentFlow` instead of building a
  sequential `Crew`; read `saved_content` / `output_path` from `flow.state`;
  fail fast (`RuntimeError`) if either is `None`; build the unchanged
  `RunResult`. Removed the sequential-pipeline imports (`Crew`, `Process`,
  `build_agents`, `build_tasks`, `save_post`) from `crew.py`; updated module and
  function docstrings to describe the flow-based path.
- `[Modify]` **`flow.py` guards**: four `ValueError` → `RuntimeError`.
- `[Modify]` **`tests/test_output.py`**: unpack the new tuple at all call sites;
  add an assertion that returned content equals the written content.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | The failure path (`handle_failure` saving the best-scoring attempt) has not been exercised by a live run — `make demo` passed on the first cycle (score 90) | Open | By design hard to force with a real LLM; Stage C integration tests (mocked Ollama) cover pass / retry-then-pass / cap-exhaustion deterministically |
| Low | Dead code from the migration (`build_tasks`, sequential-`Crew` helpers, orphaned tests) remains in the tree | Open | Backlog item added; remove as an isolated PR |
| Low | mypy remains blind through `self.state` (typed `Any`); the terminal-node logic that sets `saved_content` gets no static protection | Open (structural) | Rely on `make demo` now; Stage C integration tests are the durable net |

## 4. Milestones
- [x] **M3 DoD #1** — `@start`/`@listen`/`@router` replace `Process.sequential` as the **active** path
  - **Verification**: `crew.run()` kicks off `ContentFlow`; `make demo` ran the
    full flow end to end and saved `post_tech-pulse_20260729_202949_90a372.md`
    (editor score 90, "save" branch). `__main__.py` unchanged; `RunResult`
    contract preserved.
  - **Status**: Verified
- [x] **Stage B complete** — `run()` sources `content`/`output_path` from `flow.state` with a single source of truth for saved text
  - **Verification**: `make ci` green after each of the four commits; the
    `test_output` contract assertion pins `save_post`'s new return.
  - **Status**: Verified
- [ ] **M3 DoD #4** — integration tests with mocked Ollama — Pending (Stage C)
- [ ] **M3 DoD #5** — `make demo` shows the retry count — Pending (Stage D)

## 5. Learning Notes

### Commands / Code
- Command: VS Code "Find All References" (`Shift+F12`) vs full-text search (`Ctrl+Shift+F`)
  - Purpose: enumerate every caller of a function before changing its signature.
  - Key parameters: Find All References is language-aware (resolves the actual
    symbol); full-text search also matches unrelated same-name strings.
  - Verification: the reference list is the blast radius; here it surfaced
    `crew.py`, both terminal nodes, and `test_output` as `save_post` callers.
- Command: unpack-and-discard `path, _ = save_post(...)`
  - Purpose: adapt call sites to a function that now returns a tuple when only
    the first element is needed.
  - **Lesson**: `_` reads as "second value received, deliberately unused" —
    clearer than indexing `[0]`, and it self-documents that the function returns
    more than one value.
- Command: `uv run python -m crewai_factory --persona ...` (via `make demo`)
  - Purpose: run the real end-to-end pipeline through the package entry point.
  - **Lesson**: running a module file directly (`python src/.../crew.py`) does
    nothing when the file only defines functions and has no `__main__` block; the
    entry point is `__main__.py`, invoked with `-m`.

### Concepts / Architecture
- Concept: **Single source of truth for a produced value**
  - One-line explanation: the value that describes an action's result should come
    from whatever performed the action, not from what the caller believed it
    requested.
  - Role in this project: `saved_content` is set from `save_post`'s return, so
    "returned == written" holds by construction on both flow exits.
- Concept: **Type narrowing to satisfy a non-optional contract**
  - One-line explanation: an `if x is None: raise` guard narrows `str | None` to
    `str` for the code below it, checked by mypy without `cast` or `# type: ignore`.
  - Role in this project: `run()` narrows `saved_content`/`output_path` before
    building `RunResult`; same tool used to narrow `EditorVerdict` on 2026-07-28.
- Concept: **`ValueError` vs `RuntimeError`**
  - One-line explanation: `ValueError` = a caller passed a bad value;
    `RuntimeError` = a state that should not occur at this point in execution.
  - Role in this project: the flow guards describe impossible internal states, so
    `RuntimeError` is the accurate class.
- Concept: **Scope discipline in commits**
  - One-line explanation: one commit does one thing; adjacent improvements
    (error-class cleanup, dead-code removal) get their own commits or backlog
    items rather than riding along.
  - Role in this project: kept the wiring commit, the `RuntimeError`
    reclassification, and the dead-code removal as three separate concerns.

## 6. Next Steps
- [ ] **Stage C**: integration tests with mocked Ollama — pass-first,
  retry-then-pass, cap-exhaustion — asserting on `state.attempts` and the chosen
  terminal branch (including `saved_content` on the failure path).
- [ ] **Stage D**: `make demo` verbose log surfaces the retry count (DoD #5).
- [ ] **Stage E**: README/mermaid update (flip the FAIL edge to the real loop),
  finalize devlog, open PR → squash merge.
- [ ] **Backlog**: remove migration dead code (`build_tasks`, sequential-`Crew`
  helpers, orphaned tests) as an isolated PR.
- [ ] Open a draft PR for `feat/m3-flow-skeleton` so CI runs on every push
  (carried over — feature branches do not trigger CI).

## 7. Open Questions
- (Deferred, unchanged) `output_pydantic` parse failure fails fast — revisit only
  with real-run failure-rate evidence.
- (Deferred, unchanged) Whether Dependabot security updates are enabled (only
  alerts observed); verify the repository setting.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-29
Latest progress:
  - Current phase: M3 (CrewAI Flow) on branch feat/m3-flow-skeleton.
    Stage B (wire run() into the Flow) is DONE, committed, and pushed
    (branch HEAD 6dbd5db). Working tree clean.
  - Completed today: save_post returns (path, content); ContentState.saved_content;
    both terminal nodes record saved_content from save_post's return; run()
    kicks off ContentFlow, reads saved_content/output_path from flow.state,
    fails fast (RuntimeError) if either is None, builds the unchanged RunResult;
    four flow.py guards reclassified ValueError -> RuntimeError.
  - Verified LIVE via `make demo`: full flow ran end to end, editor score 90,
    saved to output/ on the "save" branch. M3 DoD #1 met (Flow is the active path).
  - In progress: nothing mid-flight; next is Stage C.

Current architecture summary:
  - Python 3.12 + CrewAI 1.15.2. crew.run() now kicks off ContentFlow (the
    legacy sequential Crew in run() is gone). ContentFlow: generate_topic
    (@start) -> write_draft (@listen(or_(generate_topic,"retry"))) -> edit_draft
    (@listen, output_pydantic=EditorVerdict) -> route_verdict (@router:
    save/retry/failed) -> save_output ("save") / handle_failure ("failed").
  - Gate is code-side: score >= Settings.quality_threshold (default 85).
    ContentState: topic, post, verdict, max_attempts=3, attempts, output_path,
    saved_content. Both terminal nodes set output_path AND saved_content from
    save_post's (path, content) return. run() reads both from flow.state.
  - save_post returns tuple[Path, str]; test_output pins "returned == written".
  - build_tasks + sequential-Crew helpers are now DEAD CODE (unreferenced by
    crew.py) but still in the tree; removal is a backlog item / separate PR.
  - mypy is blind through self.state (Any); rely on running + Stage C tests.

Next steps:
  - Stage C: integration tests with mocked Ollama (pass / retry-then-pass /
    cap-exhaustion), asserting state.attempts and the terminal branch taken.
  - Stage D: make demo shows retry count (DoD #5).
  - Stage E: README/mermaid, finalize devlog, PR -> squash merge.
  - Remove migration dead code (backlog).
  - Open a draft PR so CI runs on the feature branch.

For AI to be aware of:
  - Repo is PUBLIC; English-only engineering layer; never reference pre-public
    devlog IDs in public docs.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads. Confirm
    writes by re-fetching the remote, not by tool success messages.
  - Code work runs in Claude Code inside WSL so `make ci` uses the real env;
    Cowork handles non-code work.
  - TEACHING MODE (教學模式): was ON for the Stage B code work today, OFF for this
    wrap-up. It is a per-session toggle Stan controls — do NOT assume it is
    always on. When ON: Claude gives direction, hints, risk flags, and reviews
    Stan's diffs; Claude does NOT write the implementation — Stan writes the code.
    One small step at a time; mark knowledge layers; point out problems directly;
    ask a guiding question rather than hand over the answer.
  - M3 TEACHING CURRICULUM — continuity requirement (READ THIS BEFORE PLANNING
    STAGE C): M3 is taught as ONE fixed 5-stage curriculum, designed 2026-07-28.
    A new session MUST continue this exact stage breakdown and NOT re-partition
    the remaining work into a different set of stages — re-cutting the stages is
    what causes confusion across sessions. The stages and their status:
      A. Close the flow loop (route_verdict + terminal nodes)          — DONE 2026-07-28
      B. Wire into the app: crew.run() drives the Flow, RunResult kept  — DONE 2026-07-29 (today)
      C. Integration tests with mocked Ollama: three paths —
         pass-first-try / retry-then-pass / cap-exhaustion — asserting
         state.attempts and the terminal branch taken (incl. saved_content
         on the failure path)                                          — NEXT
      D. Observability: `make demo` verbose log shows the retry count (DoD #5) — pending
      E. Wrap up: README/mermaid (flip the FAIL edge to the real loop),
         finalize devlog, ROADMAP reconciliation, PR -> squash merge   — pending
    Resume at Stage C. Keep A–E as the map; if teaching mode is ON, teach Stage C
    one small step at a time within this frame.
  - Technical failures fail fast (2026-07-20); best-attempt-on-failure on cap
    exhaustion (2026-07-20). Editor is score-only; gate is code-side (>= 85).
    OLLAMA_MODEL default stays a cloud model (2026-07-16).
  - Unresolved deployment security issues go to private notes (private archive
    repo, named only in CLAUDE.local.md); currently zero open items.
  - chromadb CVE-2026-45829 (Critical, no fix) is open, assessed unreachable
    (CrewAI memory not enabled). Re-assess if memory is turned on or at M4.
```

---

## 9. ROADMAP Reconciliation

Required by the daily wrap-up. Each dimension gets an explicit conclusion.

### Milestone status — **needs update**

`docs/ROADMAP.md` still shows M3 as "📋" with "Status: All M3 entry conditions
met" and describes M3 as not-yet-started. That is now stale: M3 is in progress
and three of five DoD items are met (#1 today, #2 and #3 on 2026-07-28). When the
M3 PR lands on `main`, the ROADMAP M3 section should be updated to reflect
in-progress status and the DoD checklist state. Not editing it this session
(ROADMAP edits ride with the M3 PR in Stage E to avoid a separate docs PR through
the ruleset).

### Backlog — **needs update**

One addition for §3 Backlog: remove the migration dead code (`build_tasks`,
sequential-`Crew` helpers, orphaned tests) as an isolated PR. Carried-over
candidates from 2026-07-27 (verify/enable Dependabot security updates; revisit
`dependabot.yml` grouping; track chromadb CVE; adopt draft PRs on feature
branches) remain valid and unrecorded in §3; fold them in with the Stage E docs
pass.

### Active Decisions Log — **no change**

Today's decisions are implementation-level (return shape, error class, commit
scoping); none change milestone structure or ordering, so the Decisions Log
threshold is not met.

### Changelog — **no change until merge**

`main` did not change today; all work is on `feat/m3-flow-skeleton`. The
Changelog line lands when the M3 PR merges (Stage E).

---

*Draft — not yet written to the repository. Requires Stan's approval before
commit; then land on `feat/m3-flow-skeleton` via the normal branch workflow.*

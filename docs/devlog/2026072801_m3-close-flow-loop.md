# 2026-07-28: Close the M3 ContentFlow loop and verify retry-until-pass live

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: In Progress
**Related commits / PRs**: branch `feat/m3-flow-skeleton` — `53d4dfd` (route_verdict + editor-output typing), `cd1e109` (terminal nodes: save_output, handle_failure, output failed-marker)

---

## TL;DR
Closed the M3 `ContentFlow` loop: implemented the three remaining stub nodes
(`route_verdict` router, `save_output`, `handle_failure`), fixed the
pre-existing editor-result typing in `edit_draft`, removed the vestigial
`final_post` field, and extended `output.save_post` with a backward-compatible
`failed` marker. A first live smoke test proved retry-until-pass end to end:
cycle 1 scored 78 (fail, below the 85 threshold) → loop → cycle 2 scored 88
(pass) → saved. This matters because mypy is blind through `self.state` (typed
`Any`), so the flow's logic is only provable by running it. The flow works in
isolation but is **not yet the active path** — `crew.py run()` still drives the
legacy sequential pipeline; wiring the Flow into the CLI is stage B.

## 1. Decisions

### Decision 1: Save the writer's draft (`self.state.post`), and delete `final_post`
- **What**: The "save" path persists `self.state.post`. `EditorVerdict.final_post`
  and the matching `expected_output` line are removed.
- **Why**: The editor was narrowed to score+feedback only (2026-07-21). A
  `final_post` "polished" by the editor could diverge from the text that was
  actually scored, breaking the invariant "the saved text is exactly the text
  that scored >= threshold". Its default `""` would have needed a fallback
  anyway.
- **Alternatives considered**: Keep `final_post` — rejected as a dead,
  ambiguous-ownership field.
- **Risks & mitigations**: None significant; `attempts[]` still preserves every
  draft.

### Decision 2: Mark failed runs via a backward-compatible `failed` flag on `output.save_post`
- **What**: `output.save_post` gains a keyword-only `failed: bool = False`. When
  `True`, it adds a `**Status**: FAILED` header line and a `_failed` filename
  suffix (option a + c from discussion). Persistence logic stays in the output
  module.
- **Why**: Keep the "how to persist" concern in one place; a default of `False`
  preserves the exact prior output so legacy callers and `test_output` stay
  green.
- **Alternatives considered**: Prepend the marker in the caller (scatters the
  logic); filename-only marker (loses the in-file record).
- **Risks & mitigations**: Touches a shared, tested function — mitigated by the
  behavior-preserving default and confirmed by `make ci` (all 25 tests green).

## 2. System Changes
- `[Add]` **`flow.ContentFlow` terminal nodes**: `route_verdict` (`@router`;
  returns `"save"` if `score >= quality_threshold`, else `"retry"` while
  `len(attempts) < max_attempts`, else `"failed"`), `save_output`
  (`@listen("save")`), `handle_failure` (`@listen("failed")`; saves the
  best-scoring attempt via `max(attempts, key=score)`, marked failed).
- `[Add]` **`ContentState.output_path`** (`Path | None`): where the terminal
  nodes record the saved file path for the caller to read after `kickoff()`.
- `[Modify]` **`flow.edit_draft`**: narrow `crew.kickoff()` result to
  `CrewOutput`, then narrow `result.pydantic` to `EditorVerdict` (isinstance
  guards); dropped the now-redundant `is None` check.
- `[Modify]` **`output.save_post` + `_safe_filename`**: keyword-only
  `failed: bool = False`; failed runs get a header status line and a `_failed`
  filename suffix. Default preserves prior behavior.
- `[Remove]` **`tasks.EditorVerdict.final_post`** and the corresponding
  `expected_output` line — vestigial once the editor became score-only.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | Editor scoring is non-deterministic: cycle 2 scored 88 vs cycle 1's 78 without materially revising content or acting on feedback | Open | Model-quality, not engineering. The `attempts` trajectory is exactly the raw data to evaluate "does feedback improve scores" in M5+ |
| Low | On the pass path the editor's feedback is generated but unused | Open (accepted) | Not a separate LLM call (same response, marginal tokens); feedback is still stored in `attempts` as M5+ data. Revisit only if token cost matters |
| Low | mypy is blind through `self.state` (typed `Any`) — flow-node logic gets ~zero static protection | Open (structural) | Rely on the smoke test now; integration tests (stage C) are the durable net |

## 4. Milestones
- [x] **M3 flow loop closed** (three terminal stubs implemented)
  - **Verification**: `make ci` green (ruff + mypy + 25 pytest); code reviewed.
  - **Status**: Verified
- [x] **Retry-until-pass demonstrated end to end** (M3 DoD #2)
  - **Verification**: live smoke run via a throwaway `ContentFlow(...).kickoff()`;
    `attempts == 2`, cycle 1 score 78 (fail) → cycle 2 score 88 (pass) → saved to
    `output/` with a filename lacking the `_failed` suffix (i.e., the "save"
    branch).
  - **Status**: Verified
- [x] **M3 DoD #3** — structured verdict + router branches on typed fields
  - **Verification**: `edit_draft` uses `output_pydantic=EditorVerdict`;
    `route_verdict` branches on `verdict.score` (typed), never free text.
  - **Status**: Verified
- [ ] **M3 DoD #1** — `@start`/`@listen`/`@router` replace `Process.sequential`
  as the **active** path
  - **Status**: Pending — the flow runs in isolation, but `crew.py run()` still
    drives the sequential pipeline (stage B).
- [ ] **M3 DoD #4** — integration tests with mocked Ollama — Pending (stage C).
- [ ] **M3 DoD #5** — `make demo` shows the retry count — Pending (stage D).

## 5. Learning Notes

### Commands / Code
- Command: `git diff` / `git diff --staged` / `git diff <file>`
  - Purpose: inspect unstaged vs staged changes; scope to one file.
  - Key parameters: `--staged` (aka `--cached`) shows what is staged; bare
    `git diff` shows working-tree-vs-index.
  - Verification: the printed hunks are the change.
- Command: `git stash` / `git stash pop` (+ `git restore .`)
  - Purpose: shelve working changes to test a clean state, then restore them.
  - **Lesson**: if the clean-state run modified files (e.g. an auto-formatter),
    discard those with `git restore .` **before** `git stash pop` to avoid a
    conflict. Stash is a safe box: nothing is lost even on conflict.
- Command: `git log --oneline -N`, `git status`
  - **Lesson**: the truth about what is committed / uncommitted is `git`, not
    memory. `nothing to commit` means it is already in.
- Command: `reveal_type(expr)` + `uv run mypy src/`
  - Purpose: print mypy's inferred type for an expression (built-in, no import);
    remove the line afterward.
  - Role: used to confirm `self.state` is effectively `Any`.
- Code: `max(iterable, key=lambda x: x.attr)`
  - **Lesson**: returns the single best element and does **not** mutate. Contrast
    `list.sort()` (in-place, returns `None` — `x.sort(...)[0]` crashes) vs
    `sorted()` (returns a new list).
- Code: keyword-only parameters (a bare `*` in the signature)
  - **Lesson**: everything after `*` must be passed by name. `save_post`'s `now`
    is a **clock-injection seam** for deterministic tests; `failed` follows the
    same pattern so call sites read explicitly.
- Code: f-string with a backslash inside the `{...}` expression
  - **Lesson**: only valid on Python 3.12+ (PEP 701); a `SyntaxError` on 3.11.
    Works here because the project is pinned to 3.12.

### Concepts / Architecture
- Concept: **Type narrowing / `union-attr`**
  - One-line: a `union-attr` error means you accessed an attribute not present on
    every member of a union; fix by narrowing with an `isinstance` guard
    (runtime-checked, preferred) over `cast` (unchecked) or `# type: ignore`.
  - Role: fixed `crew.kickoff()` (→ `CrewOutput`) and `result.pydantic`
    (→ `EditorVerdict`) in `edit_draft`.
- Concept: **`self.state` is `Any`**
  - One-line: CrewAI's `Flow.state` is loosely typed, so mypy gives near-zero
    protection inside flow nodes.
  - Role: explains why a `None[0]` bug passed `make ci`; the real net is
    running + integration tests.
- Concept: **`@router` labels are a contract**
  - One-line: the router returns a label string that must exactly match the
    downstream `@listen` labels and the `or_(..., "retry")` loop; a typo breaks a
    branch silently.
- Concept: **Guard clause vs flat multi-way return**
  - One-line: a guard rejects invalid input up front (usually `raise`); the
    router's three `return`s are the main decision, not guards. A half-way guard
    that leaves state unset is the worst option.
- Concept: **Role clarity: `output_dir` vs `output_path`**
  - One-line: the directory to save into (input, from settings) is not the full
    path a save returns (output).
- Concept: **Extending a shared, tested function**
  - One-line: a new parameter's default must preserve existing behavior so
    existing callers and tests keep passing (proven by `test_output` staying
    green).
- Concept: **Premature optimization**
  - One-line: quantify the real cost before optimizing — the "unused" editor
    feedback is marginal tokens in one response, not a separate call.

## 6. Next Steps
- [ ] **Stage B**: rewire `crew.py run()` to `kickoff` `ContentFlow`, keeping the
  `RunResult(content, persona, output_path)` contract so `__main__.py` is
  unchanged. (See Open Questions for the content-source design point.)
- [ ] After stage B: `build_tasks` + the sequential `Crew` in `run()` become dead
  code — decide whether to remove them in the same PR.
- [ ] **Stage C**: integration tests with mocked Ollama
  (pass-first / retry-then-pass / cap-exhaustion), asserting on `state.attempts`.
- [ ] **Stage D**: `make demo` verbose log shows the retry count (DoD #5).
- [ ] **Stage E**: README/mermaid update (flip the FAIL edge to the real loop),
  devlog, PR → squash merge.
- [ ] Push `feat/m3-flow-skeleton` to origin (2 local commits currently unpushed)
  as a remote backup.

## 7. Open Questions
- **Stage B content source**: on the failure path `handle_failure` saves the
  best-scoring attempt, which may differ from `state.post` (the last draft). How
  should `run()` obtain the content that was actually saved for
  `RunResult.content`? Candidate: have both terminal nodes record the final saved
  content in a single `ContentState` field (set `state.post` to the saved text,
  or add a dedicated field) so `run()` reads one place. Decide at the start of
  stage B.
- (Deferred, unchanged) `output_pydantic` parse failure fails fast — revisit only
  with real-run failure-rate evidence.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-28
Latest progress:
  - Current phase: M3 (CrewAI Flow) on branch feat/m3-flow-skeleton.
    Stage A (close the flow loop) is DONE and committed (HEAD cd1e109);
    2 local commits unpushed. Working tree clean.
  - Completed today: route_verdict (@router), save_output, handle_failure
    (best-scoring attempt, failed marker); ContentState.output_path;
    edit_draft result/verdict typing narrowed; final_post removed;
    output.save_post gained a backward-compatible failed marker.
  - Verified LIVE via smoke test: retry-until-pass works
    (cycle1 78 fail -> cycle2 88 pass -> saved). Flow runs in isolation.
  - In progress: nothing mid-flight; next is Stage B.

Current architecture summary:
  - Python 3.12 + CrewAI 1.15.2. ContentFlow: generate_topic (@start) ->
    write_draft (@listen(or_(generate_topic,"retry")), injects verdict.feedback
    on retries) -> edit_draft (@listen, output_pydantic=EditorVerdict, appends
    one Attempt/cycle) -> route_verdict (@router: save/retry/failed) ->
    save_output ("save") / handle_failure ("failed").
  - Gate is code-side: score >= Settings.quality_threshold (default 85).
    ContentState: topic, post, verdict, max_attempts=3, attempts, output_path.
    Cycle count is len(attempts). Each node runs a single-agent Crew.
  - IMPORTANT: crew.py run() STILL drives the legacy sequential pipeline; the
    Flow is not the active CLI path yet. Wiring it in is Stage B.
  - mypy is blind through self.state (Any); rely on running + tests.

Teaching context (IMPORTANT for continuing):
  - Mode: 教學模式 ON. Claude gives direction + hints and reviews; Stan writes
    the code himself. Claude does NOT write the implementation. One small step
    at a time; mark knowledge layers; point out problems directly.
  - Curriculum (5 stages), designed 2026-07-28:
    A. Close the loop (route_verdict + terminal nodes)  -- DONE
    B. Wire into app: crew.py run() drives the Flow, keep RunResult contract
    C. Integration tests (mocked Ollama): pass / retry-pass / cap-exhaustion
    D. Observability: make demo shows retry count (DoD #5)
    E. Wrap up: README/mermaid, devlog, PR -> squash merge
  - Resume at Stage B. First thing to settle: the content-source design
    question (see Open Questions).

Next steps:
  - Stage B: crew.py run() -> ContentFlow.kickoff(); build RunResult from
    flow.state (output_path from state; content = the saved text). Then decide
    whether to delete the now-dead build_tasks / sequential Crew.
  - Stage C tests; Stage D demo visibility; Stage E README + PR.
  - Push the branch to origin as backup.

For AI to be aware of:
  - Repo is PUBLIC; English-only engineering layer; never reference pre-public
    devlog IDs in public docs.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads. Confirm
    writes by re-fetching the remote, not by tool success messages.
  - Squash merge means feature-branch commit granularity is your own save-point,
    not main's public history.
  - Technical failures fail fast (2026-07-20); best-attempt-on-failure on cap
    exhaustion (2026-07-20). OLLAMA_MODEL default stays a cloud model
    (2026-07-16). Editor is score-only; gate is code-side (>= 85).
  - Unresolved deployment security issues go to private notes (archive repo
    crewai-factory-docker); currently zero open items.
```

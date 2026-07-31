# 2026-07-30: Add mocked-Ollama integration tests for the ContentFlow (M3 Stage C)

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: Completed (M3 Stage C)

---

## TL;DR
Completed M3 Stage C: `tests/test_flow.py` now covers the whole `ContentFlow`
control loop with three deterministic, network-free integration tests —
pass-first-try, retry-then-pass, and cap-exhaustion — satisfying **M3 DoD #4**.
The LLM is cut out at a single seam: `Crew.kickoff` is replaced (via pytest's
`monkeypatch`) with a `Mock(side_effect=[...])` that dispenses a scripted,
ordered list of fake `CrewOutput` objects, one per node call. A small
`fake_output()` helper builds those fakes: plain text for the topic/writer
nodes, and a real `CrewOutput` carrying an `EditorVerdict(score=...)` for the
editor node (the editor fake **must** be a genuine `CrewOutput` to pass the
node's `isinstance` check). The failure-path test deliberately uses **distinct
draft contents plus descending scores** (80 → 75 → 70) so that its
`saved_content == "draft01"` assertion actually discriminates "save the
best-scoring attempt" from "save the last attempt" — the exact `max()` logic
that `make demo` could never exercise. Full `make ci` is green (ruff, ruff
format, mypy on `src/`, 28 tests). Three of five M3 DoD items are now met (#1
Flow is active, #2 retry-until-pass, #3 structured verdict, and now #4
integration tests); Stages D and E remain.

## 1. Decisions

### Decision 1: Mock the LLM at the `Crew.kickoff` seam, not at the agents or the state
- **What**: The tests replace **one** thing — the `kickoff` method on the
  `Crew` class — with a `Mock` whose `side_effect` is an ordered list of fake
  `CrewOutput` objects. Everything else in the flow (the `@start`/`@listen`/
  `@router` wiring, `ContentState` mutation, the route logic, both terminal
  nodes) runs for real.
- **Why**: The only non-deterministic, network-bound dependency is the LLM, and
  every node reaches it through the same line: `crew.kickoff()`. Patching that
  single class method is the smallest cut that removes the LLM from all three
  node types at once, while leaving the actual control flow — the thing under
  test — intact. This is "mock only at the boundary": the more internal
  machinery you fake, the more the test verifies your fakes instead of your code.
- **Alternatives considered**:
  - (a) Fake/inject `ContentState` with pre-filled attempts and scores —
    **rejected**: `ContentState` is the flow's own output, not an external
    dependency. Faking it would short-circuit the very logic (append attempt,
    route on score, pick best on failure) the test exists to verify. That is the
    over-mocking anti-pattern.
  - (b) Replace the agents / their LLM objects — **rejected**: harder to script
    an exact per-cycle score sequence, and couples the test to how CrewAI
    assembles prompts and parses output internally.
  - (c) Intercept HTTP / the Ollama client at the lowest level — **rejected**:
    most realistic but most brittle; it would test CrewAI's parsing of raw LLM
    responses, well beyond the goal of verifying our own flow wiring.
- **Risks & mitigations**: Patching a class method reaches every instance,
  including the crews built later inside `flow.kickoff()` — relied on
  intentionally (method lookup resolves on the class, shared by all instances).
  `monkeypatch` (the fixture, not a hand-instantiated `MonkeyPatch`) auto-restores
  the original after each test, so the patch cannot leak across tests.

### Decision 2: Make the failure-path assertion discriminating (distinct drafts + descending scores)
- **What**: The cap-exhaustion test feeds three **different** draft bodies
  (`draft01`, `draft02`, `draft03`) with **descending** scores (80, 75, 70), and
  asserts `saved_content == "draft01"`.
- **Why**: `handle_failure` saves `max(attempts, key=score).content` — the
  best-scoring attempt. If all three drafts shared the same body, "save the best"
  and "save the last" would produce identical files, and the assertion could not
  tell a correct implementation from a regression (e.g. someone changing `max()`
  to `attempts[-1]`). Descending scores put the best (80) on the **first** draft
  and the last (70) on a **different** draft, so the assertion fails if the code
  ever stops picking the best. A good test must be able to fail when the code is
  wrong.
- **Alternatives considered**: Identical drafts + assert only that a file was
  saved — rejected: green regardless of the best-vs-last logic, i.e. no
  discriminating power over the one branch this test exists to protect.
- **Risks & mitigations**: The score/draft coupling is documented inline so the
  intent is not lost in a future edit.

### Decision 3: `fake_output()` is a plain helper in the test file, not a fixture in conftest
- **What**: The fake-`CrewOutput` factory is a module-level function in
  `tests/test_flow.py`, called many times per test to build the `side_effect`
  list; it is not a pytest fixture and does not live in `conftest.py`.
- **Why**: A fixture is injected once per test as a prepared value; this helper
  must be **called repeatedly with different arguments** (mainly a varying
  `score`) to assemble an ordered list — that is a plain function's job, not a
  fixture's. `conftest.py` is reserved for cross-file fixtures; a helper used
  only by the Stage C flow tests belongs beside them.
- **Alternatives considered**: A "factory fixture" (a fixture returning a
  function) — rejected as unnecessary indirection for a single test module.
- **Risks & mitigations**: If a second test module later needs the same helper,
  promote it to a shared `tests/` helper module at that point (not pre-emptively).

## 2. System Changes
- `[Add]` **`tests/test_flow.py`**: a `TestContentFlow` class with three
  integration tests (`test_flow_pass_first`, `test_flow_retry_then_pass`,
  `test_flow_cap_exhaustion`) and a module-level `fake_output()` helper that
  builds fake `CrewOutput` objects (plain-text for topic/writer nodes; a real
  `CrewOutput` carrying an `EditorVerdict` for the editor node). Tests use the
  existing `sample_persona` / `settings` fixtures from `conftest.py`, patch
  `Crew.kickoff` via `monkeypatch`, and assert on `state.topic`,
  `state.verdict.score`, `len(state.attempts)`, and `state.saved_content`.
- No production code changed this session; `src/` is untouched. Stage C is
  purely additive test coverage.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | Failure path (`handle_failure` saving the best-scoring attempt) was previously unexercised — `make demo` only ever passed on the first cycle | **Resolved (deterministic case)** | `test_flow_cap_exhaustion` now covers it with a discriminating `saved_content` assertion |
| Low | The terminal branch (save vs failure) is asserted **indirectly** — via `attempts` length and `saved_content` value — rather than by observing the branch label directly | Open (acceptable) | Content + attempt-count pin the branch unambiguously today; revisit only if a case needs an explicit branch assertion |
| Low | mypy remains blind through `self.state` (typed `Any`); terminal-node logic gets no static protection | Open (structural, carried) | Integration tests are the durable net; unchanged from 2026-07-29 |
| Low | CrewAI emits `DeprecationWarning`s during agent construction (agents are built but never call the LLM, since `kickoff` is mocked) | Open (cosmetic) | Not our code; no action for Stage C |

## 4. Milestones
- [x] **M3 DoD #4** — integration tests with mocked Ollama covering the full Flow paths
  - **Verification**: `make ci` green — `ruff check` + `ruff format --check` on
    `src/ tests/`, `mypy src/`, and `pytest` with **28 passed** (including the 3
    new `test_flow.py` tests). Each test asserts `state.attempts` length and the
    resulting `saved_content` for its path (pass-first → 1 attempt / `draft01`;
    retry-then-pass → 2 attempts / `draft02`; cap-exhaustion → 3 attempts /
    `draft01`, the best-scoring attempt).
  - **Status**: Verified
- [ ] **M3 DoD #5** — `make demo` surfaces the retry count — Pending (Stage D)

## 5. Learning Notes

### Commands / Code
- Command: `monkeypatch.setattr(Crew, "kickoff", Mock(side_effect=[...]))`
  - Purpose: replace the LLM-calling method on the `Crew` **class** with a
    scripted stand-in for the duration of one test.
  - Key parameters: `side_effect=<list>` makes the `Mock` return the list's next
    element on each call (raising `StopIteration` if called more times than
    scripted — a free check on call count); patching the **class** attribute
    covers every instance, including crews created later inside `flow.kickoff()`.
  - Verification: `uv run pytest tests/test_flow.py -v`.
  - Rollback: none needed — the `monkeypatch` fixture auto-restores the original
    method at test teardown.
- Command: `make ci` (= `ruff check` + `ruff format --check` on `src/ tests/`,
  `mypy src/`, `pytest`)
  - Purpose: the full local gate; passing green is the definition-of-done check.
  - Key parameters / gotcha: `typecheck` runs `mypy src/` **only** — test files
    are not type-checked, so untyped fixture params would not fail CI; ruff,
    however, **does** lint and format-check `tests/`. Test method params were
    annotated anyway to match the project convention (see `test_output.py`).
  - Rollback: `make format` auto-fixes ruff formatting/import-order findings.

### Concepts / Architecture
- Concept: **Unit test vs integration test**
  - One-line explanation: a unit test verifies one component in isolation; an
    integration test verifies that several components collaborate correctly.
  - Role in this project: `test_output.py` unit-tests `save_post`; `test_flow.py`
    integration-tests the whole `generate → write → edit → route → terminal`
    wiring, which no single-unit test can reach.
- Concept: **Seam** (a place to substitute behaviour without editing the code
  under test)
  - One-line explanation: pick the seam at the external boundary; replace the
    dependency there and let everything inside run for real.
  - Role in this project: `Crew.kickoff` is the seam between our flow and the LLM.
- Concept: **Mock at the boundary, not the internal state**
  - One-line explanation: fake the external dependency (LLM output), never the
    thing you are trying to verify (`ContentState`).
  - Role in this project: faking `ContentState` would have short-circuited the
    route/attempt/best-pick logic the tests exist to protect.
- Concept: **Test discriminating power**
  - One-line explanation: a test should fail when the implementation is wrong;
    inputs must be chosen so correct and incorrect behaviour diverge in the
    assertion.
  - Role in this project: distinct drafts + descending scores make
    `saved_content == "draft01"` distinguish "save best" from "save last".
- Concept: **Fixtures are injected, not imported**
  - One-line explanation: request a fixture by naming it in a test's parameter
    list; pytest auto-discovers `conftest.py` fixtures and runs them for you.
  - Role in this project: the tests take `sample_persona`, `settings`,
    `monkeypatch` as parameters rather than importing or constructing them.
- Concept: **Class vs instance method lookup**
  - One-line explanation: methods live on the class; every instance shares them,
    so replacing the class attribute affects all instances, even ones created
    later.
  - Role in this project: patching `Crew.kickoff` once covers all the crews the
    flow builds internally.
- Concept: **A type annotation is a real name reference**
  - One-line explanation: annotating `x: Persona` uses the name `Persona`, which
    must be importable in the file; without `from __future__ import annotations`
    it is even evaluated at runtime and raises `NameError` if unimported.
  - Role in this project: annotating the test params required importing
    `Persona`, `Settings`, and `pytest`.

## 6. Next Steps
- [ ] **Commit Stage C** — commit `tests/test_flow.py` on its own
  (`test: add ContentFlow integration tests (pass / retry / cap-exhaustion)`).
- [ ] **Stage D** — `make demo` verbose log surfaces the retry count (DoD #5):
  decide where the attempt/cycle number is read (`state.attempts`) and which node
  logs it.
- [ ] **Stage E** — README/mermaid (flip the FAIL edge to the real loop),
  finalize devlog, ROADMAP reconciliation, PR → squash merge.
- [ ] **Backlog** — remove migration dead code (`build_tasks`, sequential-`Crew`
  helpers, orphaned tests) as an isolated PR.
- [ ] Open a draft PR for `feat/m3-flow-skeleton` so CI runs on every push.

## 7. Open Questions
- (Carried, unchanged) Whether an explicit terminal-branch assertion is worth
  adding, or whether `attempts` + `saved_content` remain sufficient.
- (Deferred, unchanged) `output_pydantic` parse failure fails fast — revisit only
  with real-run failure-rate evidence.
- (Deferred, unchanged) Whether Dependabot security updates are enabled (only
  alerts observed); verify the repository setting.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-30
Latest progress:
  - Current phase: M3 (CrewAI Flow) on branch feat/m3-flow-skeleton.
    Stage C (integration tests) is DONE and make-ci-green, but NOT yet committed
    (tests live in the working tree). First action next session: commit
    tests/test_flow.py on its own.
  - Completed today: tests/test_flow.py with a fake_output() helper and three
    deterministic integration tests (pass-first / retry-then-pass /
    cap-exhaustion). LLM mocked at the Crew.kickoff seam via
    monkeypatch + Mock(side_effect=[...]). make ci green (ruff, ruff format,
    mypy src/, 28 tests). M3 DoD #4 met.
  - In progress: nothing mid-flight; next is Stage D.

Current architecture summary (unchanged from 2026-07-29, plus test coverage):
  - Python 3.12 + CrewAI 1.15.2. crew.run() kicks off ContentFlow. Flow:
    generate_topic (@start) -> write_draft (@listen(or_(generate_topic,"retry")))
    -> edit_draft (@listen, output_pydantic=EditorVerdict) -> route_verdict
    (@router: save/retry/failed) -> save_output ("save") / handle_failure
    ("failed"). Gate is code-side: score >= Settings.quality_threshold (default 85).
  - ContentState: topic, post, verdict, max_attempts=3, attempts, output_path,
    saved_content. Both terminal nodes set output_path AND saved_content from
    save_post's (path, content) return. run() reads both from flow.state.
  - Tests: Crew.kickoff is the mock seam; each node reaches the LLM through it.
    fake_output(score=None) -> CrewOutput(raw=...) for topic/writer;
    fake_output(score=n) -> CrewOutput(raw=..., pydantic=EditorVerdict(score=n,...))
    for editor (the editor fake MUST be a real CrewOutput to pass the node's
    isinstance check). Failure-path test uses distinct drafts + descending scores
    so saved_content distinguishes "save best" from "save last".
  - build_tasks + sequential-Crew helpers remain DEAD CODE (backlog removal).
  - mypy is blind through self.state (Any); rely on the new integration tests.

Next steps:
  - Commit Stage C (tests/test_flow.py) on its own.
  - Stage D: make demo shows retry count (DoD #5).
  - Stage E: README/mermaid, finalize devlog, ROADMAP reconciliation, PR ->
    squash merge.
  - Remove migration dead code (backlog); open a draft PR so CI runs on the branch.

For AI to be aware of:
  - Repo is PUBLIC; English-only engineering layer; never reference pre-public
    devlog IDs in public docs.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads. Confirm
    writes by re-fetching the remote, not by tool success messages.
  - Code work runs in Claude Code inside WSL so `make ci` uses the real env;
    Cowork handles non-code work (this devlog was drafted in Cowork).
  - make ci detail: typecheck is `mypy src/` ONLY (tests not type-checked); ruff
    lints+format-checks BOTH src/ and tests/. Annotate test params anyway to
    match convention (test_output.py).

  - TEACHING MODE (教學模式): was ON for this whole Stage C session (Stan wrote
    every line of test_flow.py; Claude gave direction, hints, risk flags, and
    reviewed diffs — Claude did NOT write the implementation). It is a per-session
    toggle Stan controls — do NOT assume it is on or off next session; wait for
    Stan to set it. When ON: one small step at a time, mark knowledge layers,
    point out problems directly, ask a guiding question rather than hand over the
    answer.

  - M3 TEACHING CURRICULUM — continuity requirement (READ BEFORE PLANNING THE
    NEXT STAGE): M3 is taught as ONE fixed 5-stage curriculum, designed
    2026-07-28. A new session MUST continue this exact stage breakdown and NOT
    re-partition the remaining work into a different set of stages — re-cutting
    the stages is what causes cross-session confusion. Stages and status:
      A. Close the flow loop (route_verdict + terminal nodes)          — DONE 2026-07-28
      B. Wire into the app: crew.run() drives the Flow, RunResult kept  — DONE 2026-07-29
      C. Integration tests with mocked Ollama: three paths —
         pass-first-try / retry-then-pass / cap-exhaustion — asserting
         state.attempts and the terminal branch taken (incl. saved_content
         on the failure path)                                          — DONE 2026-07-30 (this session)
      D. Observability: `make demo` verbose log shows the retry count (DoD #5) — NEXT
      E. Wrap up: README/mermaid (flip the FAIL edge to the real loop),
         finalize devlog, ROADMAP reconciliation, PR -> squash merge   — pending
    Resume at Stage D. Keep A–E as the map; if teaching mode is ON, teach Stage D
    one small step at a time within this frame.

  - Technical failures fail fast (2026-07-20); best-attempt-on-failure on cap
    exhaustion (2026-07-20). Editor is score-only; gate is code-side (>= 85).
    OLLAMA_MODEL default stays a cloud model (2026-07-16).
  - Unresolved deployment security issues go to private notes (private archive
    repo); currently ZERO open items.
  - chromadb CVE-2026-45829 (Critical, no fix) is open, assessed unreachable
    (CrewAI memory not enabled). Re-assess if memory is turned on or at M4.
```

---

## 9. ROADMAP Reconciliation

Required by the daily wrap-up. Each dimension gets an explicit conclusion.

### Milestone status — **needs update (deferred to Stage E PR)**
`docs/ROADMAP.md` still shows M3 as "📋" and "not yet started". That is stale:
M3 is in progress with **four of five** DoD items met (#1, #2, #3, and now #4).
Per the standing decision (2026-07-29), ROADMAP edits ride with the M3 PR in
Stage E rather than as a separate docs PR through the branch ruleset, so no edit
this session. When the PR lands, update the M3 section to in-progress with the
DoD checklist state (only #5 remaining at that point, pending Stage D).

### Backlog — **needs update (fold into Stage E)**
No new backlog item this session. Carried candidates still valid and unrecorded
in ROADMAP §3: remove migration dead code; verify/enable Dependabot security
updates; revisit `dependabot.yml` grouping; track chromadb CVE; adopt draft PRs
on feature branches. Fold these into the Stage E docs pass.

### Active Decisions Log — **no change**
Today's decisions (mock seam, test-input design, helper placement) are
test-level; none change milestone structure or ordering, so the Decisions Log
threshold is not met.

### Changelog — **no change until merge**
`main` did not change today; all work is on `feat/m3-flow-skeleton`. The
Changelog line lands when the M3 PR merges (Stage E).

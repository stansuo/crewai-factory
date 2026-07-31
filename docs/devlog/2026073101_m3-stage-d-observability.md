# 2026-07-31: Surface the retry count in the flow log (M3 Stage D, DoD #5)

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: Completed (M3 Stage D)
**Related commits / PRs**: `commit 26cf7f6`

---

## TL;DR
Completed M3 Stage D: the `ContentFlow` now emits two `loguru` INFO lines per
cycle so the retry loop is observable in `make demo`, satisfying **M3 DoD #5**
and completing **all five M3 DoD items**. `edit_draft` logs the attempt it just
scored (`Attempt {cycle}/{max} — score {n}`); `route_verdict` logs the decision
it took (`→ passed, saving` / `→ retrying` / `→ failed, saving best attempt`).
The split follows separation of concerns — each node reports the work it owns —
and reads as a natural loop with the router lines indented one level under the
attempt line. Numbers come from a single source: `edit_draft` uses its local
`cycle`; `route_verdict` reads `state.attempts[-1].cycle` rather than recomputing
`len(attempts)`, so the displayed count can never drift from the recorded
`Attempt`. Change is log-only (`+23` lines in `flow.py`, no logic touched);
`make ci` green (28 tests unchanged). A persistent file-log sink was deliberately
**not** added — deferred to M4 (see Decision 2).

## 1. Decisions

### Decision 1: Split the log across `edit_draft` (score) and `route_verdict` (decision)
- **What**: Two log statements, not one. `edit_draft` logs the attempt number and
  score right after appending the `Attempt`; `route_verdict` logs which branch it
  chose, indented under the attempt line.
- **Why**: Separation of concerns — a node should report the work it owns.
  `edit_draft` owns "score this cycle"; `route_verdict` owns "decide next step".
  Aligning each log line with the node that produced it means the shape of the log
  mirrors the shape of the control flow, which is exactly what a demo of a
  retry-until-pass loop should show. The indented router line makes each cycle
  read as `score → decision`.
- **Alternatives considered**:
  - (a) Log everything in `route_verdict` (it can read `verdict.score` too) —
    rejected: the router would then own both "decide" and "narrate the whole
    cycle", and it would be reporting a score another node computed. Acceptable,
    but it blurs the node's single responsibility for marginal terminal-conciseness
    gain.
  - (b) Also log inside `write_draft` on retry — rejected: adds a third line per
    cycle without new information; the retry is already visible from the router's
    decision line plus the next attempt line.
- **Risks & mitigations**: The two lines are only meaningful together; if a future
  edit moves the `append` out of `edit_draft`, both the count and the router's
  `attempts[-1].cycle` read would shift together (single source), so they stay
  consistent by construction.

### Decision 2: Do NOT add a persistent file-log sink; defer to M4
- **What**: Logging still goes only to the terminal (stderr, via the existing
  `setup_logging()`). No file sink was added this session.
- **Why**: DoD #5 asks only that the retry count be *visible* in `make demo`,
  which the terminal output already satisfies. "Where do I read logs later?" is a
  different, deployment-shaped need: on the production host the run is a single-run
  container triggered by a systemd timer with no human watching, so logs must land
  somewhere persistent — and the location, rotation, and retention all depend on
  the containerized layout (volume mounts, host paths). Deciding that on the dev
  machine would be premature and likely thrown away at deploy time. Keeping Stage D
  to a single responsibility (make the loop observable) also avoids scope creep.
- **Alternatives considered**: Add a `logger.add("logs/…", rotation=…,
  retention=…)` file sink now — rejected as premature per the above; recorded as a
  backlog item for M4 instead.
- **Risks & mitigations**: None for dev. Backlogged so it is not forgotten at M4
  (see §6).

## 2. System Changes
- `[Modify]` **`flow.py` / `edit_draft`**: after appending the `Attempt`, log
  `Attempt {cycle}/{max_attempts} — score {score}` at INFO, using loguru's
  parameterized form (`"…{}…", a, b` — not an f-string), matching the project
  convention in `crew.py`.
- `[Modify]` **`flow.py` / `route_verdict`**: before each `return`, log the chosen
  branch (`save` / `retry` / `failed`) at INFO, indented one level, reading the
  cycle from `state.attempts[-1].cycle`.
- `[Add]` **`flow.py` import**: `from loguru import logger` (third-party group,
  alphabetical between `crewai` and `pydantic`).
- No production logic changed; no test changed. Purely additive observability.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | The two per-cycle log lines are meaningful only as a pair; reading one without the other is less informative | Open (acceptable) | Indentation visually couples them; the pairing mirrors edit→route control flow |
| Low | loguru INFO lines are interleaved among CrewAI's own verbose panels (`Crew Completion`, `Flow Method …`), so they are not visually grouped | Open (cosmetic) | Not our output; a dedicated file sink (M4) would give a clean, greppable stream |
| Low | No persistent log for post-hoc inspection on dev | Open (by design) | Deferred to M4 deployment (Decision 2) |

## 4. Milestones
- [x] **M3 DoD #5** — `make demo` verbose log surfaces the retry count
  - **Verification**: `make ci` green (ruff, ruff format, mypy `src/`, 28 tests).
    `make demo` run observed emitting `INFO | crewai_factory.flow:edit_draft —
    Attempt 1/3 — score 92` and `INFO | crewai_factory.flow:route_verdict — →
    Attempt 1/3 passed, saving output`; the CrewAI `Crew Completion` panel showed
    the matching `Final Output: {"score":92,"feedback":…}`, confirming the logged
    count/score reflect the real structured verdict, not a hardcoded value.
  - **Status**: Verified
- [x] **M3 complete** — all five DoD items met (#1 Flow active, #2 retry-until-pass,
  #3 structured verdict, #4 integration tests, #5 observable retry count)
  - **Verification**: DoD #1–#4 verified in prior devlogs; #5 verified above.
  - **Status**: Verified (pending Stage E wrap-up: README/mermaid, ROADMAP, PR)

## 5. Learning Notes

### Commands / Code
- Command: `logger.info("Attempt {}/{} — score {}", cycle, max_attempts, score)`
  - Purpose: emit a structured INFO line using loguru's lazy parameterization.
  - Key parameters: values are passed as **arguments** with `{}` placeholders, not
    interpolated via an f-string — loguru's preferred form (avoids formatting when
    the level is filtered out; keeps the message template intact for structured
    sinks). Matches `crew.py`'s existing style.
  - Verification: `make demo`, read the terminal.
  - Rollback: remove the log lines; no state or control-flow impact.

### Concepts / Architecture
- Concept: **Separation of concerns (applied to logging)**
  - One-line explanation: a log line belongs in the node whose work it describes.
  - Role in this project: `edit_draft` logs the score it computed; `route_verdict`
    logs the decision it made, so the log's structure mirrors the flow's.
- Concept: **Single source of truth (for the cycle count)**
  - One-line explanation: the "which attempt" fact is computed once and read
    everywhere, never recomputed.
  - Role in this project: `route_verdict` reads `state.attempts[-1].cycle` instead
    of recomputing `len(attempts)`, so it can never disagree with the logged
    `Attempt`.
- Concept: **loguru sink**
  - One-line explanation: a logger can fan out to multiple destinations (sinks);
    the terminal is one, a rotating file is another.
  - Role in this project: only the stderr sink exists today; a file sink is the
    M4 mechanism for post-hoc log inspection on the production host.
- Concept: **Scope discipline / deferring by dependency**
  - One-line explanation: defer a decision to the stage that has the context to
    make it well, rather than guessing early.
  - Role in this project: file-log location depends on the container layout, so it
    belongs to M4, not Stage D.

## 6. Next Steps
- [ ] **Stage E** — README/mermaid: flip the FAIL edge to the real retry loop;
  reconcile ROADMAP (M3 → in-progress/done, DoD #1–#5 checked); open PR → squash
  merge to `main`.
- [ ] **Backlog (fold into ROADMAP in Stage E)** — Persistent file-log sink: add a
  loguru file sink (rotation + retention) for post-hoc log inspection. Deferred to
  M4: the log location and rotation strategy depend on the containerized deployment
  (single-run container + systemd timer on the production host), so deciding it on
  the dev machine would be premature.
- [ ] **Backlog (carried)** — remove migration dead code (`build_tasks`,
  sequential-`Crew` helpers, orphaned tests) as an isolated PR; verify/enable
  Dependabot security updates; revisit `dependabot.yml` grouping; track chromadb
  CVE-2026-45829 (assessed unreachable, re-assess at M4 / if memory enabled).

## 7. Open Questions
- (Carried) Whether an explicit terminal-branch assertion in the flow tests is
  worth adding, or whether `attempts` + `saved_content` remain sufficient.
- (Deferred) `output_pydantic` parse failure fails fast — revisit only with
  real-run failure-rate evidence.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-31
Latest progress:
  - Current phase: M3 (CrewAI Flow) on branch feat/m3-flow-skeleton.
    Stage D (observability, DoD #5) is DONE, committed and pushed
    (commit 26cf7f6). ALL FIVE M3 DoD items are now met. Remaining work is
    Stage E wrap-up only (docs + PR); no more code changes planned for M3.
  - Completed today: added two loguru INFO log lines to flow.py — edit_draft
    logs "Attempt {cycle}/{max} — score {n}" after appending the Attempt;
    route_verdict logs the branch taken (save/retry/failed), indented, reading
    state.attempts[-1].cycle (single source, no recompute). Log-only, +23 lines,
    make ci green (28 tests unchanged). make demo verified visually against the
    CrewAI Crew Completion panel's structured Final Output.
  - In progress: nothing mid-flight; next is Stage E.

Current architecture summary (unchanged from 2026-07-30, plus logging):
  - Python 3.12 + CrewAI 1.15.2. crew.run() kicks off ContentFlow. Flow:
    generate_topic (@start) -> write_draft (@listen(or_(generate_topic,"retry")))
    -> edit_draft (@listen, output_pydantic=EditorVerdict; appends Attempt,
    logs score) -> route_verdict (@router: save/retry/failed; logs decision)
    -> save_output ("save") / handle_failure ("failed"). Gate is code-side:
    score >= Settings.quality_threshold (default 85).
  - Logging: only the stderr sink (setup_logging in __main__.py). No file sink
    yet — deferred to M4 (location depends on container layout). loguru lines
    interleave with CrewAI verbose panels; a file sink at M4 would give a clean
    greppable stream.
  - build_tasks + sequential-Crew helpers remain DEAD CODE (backlog removal).
  - mypy is blind through self.state (Any); integration tests are the net.

Next steps (Stage E):
  - README/mermaid: flip the FAIL edge to the real retry loop.
  - ROADMAP reconciliation: M3 -> in-progress/done, DoD #1-5 checked; fold
    backlog (file-log sink -> M4; dead-code removal; Dependabot; chromadb CVE).
  - Open PR for feat/m3-flow-skeleton; wait for required check `quality`;
    squash merge to main.

For AI to be aware of:
  - Repo is PUBLIC; English-only engineering layer; never reference pre-public
    devlog IDs in public docs. Never put the production host's machine name in
    public repo (devlog/commit/ROADMAP) — it lives in private-notes only.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads. Confirm
    writes by re-fetching the remote, not by tool success messages.
  - Code work runs in Claude Code inside WSL so `make ci` uses the real env;
    Cowork handles non-code work (this devlog was drafted in Cowork).
  - make ci detail: typecheck is `mypy src/` ONLY (tests not type-checked); ruff
    lints+format-checks BOTH src/ and tests/.

  - TEACHING MODE (教學模式): was ON this session. Stan directs; Claude gives
    direction/hints/risk-flags and reviews diffs — Claude did NOT write the
    flow.py implementation (Stan wrote the log lines). Per-session toggle Stan
    controls — do NOT assume next session; wait for Stan to set it.

  - M3 TEACHING CURRICULUM — one fixed 5-stage curriculum (designed 2026-07-28).
    Do NOT re-partition. Status:
      A. Close the flow loop                    — DONE 2026-07-28
      B. Wire into the app                      — DONE 2026-07-29
      C. Integration tests (mocked Ollama)      — DONE 2026-07-30
      D. Observability: make demo retry count   — DONE 2026-07-31 (this session)
      E. Wrap up: README/mermaid, devlog, ROADMAP reconciliation, PR->squash merge
                                                — NEXT (in progress)
    Resume at Stage E.

  - Technical failures fail fast; best-attempt-on-failure on cap exhaustion.
    Editor is score-only; gate is code-side (>= 85). OLLAMA_MODEL default stays
    a cloud model.
  - Unresolved deployment security issues go to private notes (private archive
    repo); currently ZERO open items.
  - chromadb CVE-2026-45829 (Critical, no fix) open, assessed unreachable
    (CrewAI memory not enabled). Re-assess if memory is turned on or at M4.
```

---

## 9. ROADMAP Reconciliation

Required by the daily wrap-up. Each dimension gets an explicit conclusion.

### Milestone status — **needs update (do in Stage E PR)**
`docs/ROADMAP.md` still shows M3 as "📋" / not started. That is now materially
stale: **all five** M3 DoD items are met as of today. Per the standing decision
(2026-07-29), ROADMAP edits ride with the M3 PR in Stage E, not as a separate
docs PR through the branch ruleset. When the PR is prepared, update the M3
section to reflect DoD #1–#5 complete and the milestone effectively done pending
merge.

### Backlog — **needs update (fold into Stage E)**
New this session: **persistent file-log sink → M4** (Decision 2). Still-valid
carried candidates unrecorded in ROADMAP §3: remove migration dead code;
verify/enable Dependabot security updates; revisit `dependabot.yml` grouping;
track chromadb CVE; adopt draft PRs on feature branches. Fold all into the
Stage E ROADMAP pass.

### Active Decisions Log — **no change**
Today's decisions (log split, defer file sink) are stage-level implementation
choices; neither changes milestone structure or ordering, so the Decisions Log
threshold is not met.

### Changelog — **no change until merge**
`main` did not change today; all work is on `feat/m3-flow-skeleton`. The
Changelog line lands when the M3 PR merges (Stage E).

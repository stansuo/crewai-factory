# 2026-07-27: Clear the dependency backlog, harden CI, and migrate project context to Claude Code

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: Completed
**Related commits / PRs**: `#6`–`#14` (dependency updates), `#16` (CI permissions), `#17` (Claude Code migration), `main` at `c3ab2a3`

---

## TL;DR

A full day of engineering foundation work with **zero M3 feature progress** — by
choice. Nine stale dependency PRs were merged (closing 42 Dependabot alerts), the
CI workflow got a least-privilege `permissions` block, and the entire Claude
Desktop project context was migrated into `CLAUDE.md` plus `.claude/rules/` so
that development can move to Claude Code inside WSL. The M3 branch was rebased
onto the new `main` and its accumulated ruff errors fixed; `route_verdict` is
still a stub and mypy still fails. Two AI misjudgements were caught by Stan
during the day and both are now encoded as rules.

## 1. Decisions

### Decision 1: Clear the dependency backlog before resuming M3

- **What**: Merge all nine open Dependabot PRs (`#6`–`#14`) before writing any
  more Flow code.
- **Why**: Not incident response — maintenance hygiene. The PRs were CI-green
  and cheap to merge; the repo is a public portfolio where a stack of stale
  dependency PRs is a visible signal; and resolving dependency churn while
  `flow.py` was still half-written was cheaper than discovering a break after
  six more nodes were added.
- **Alternatives considered**: Continue M3 first — defensible, and cheaper in
  rebase terms, because Dependabot rebases its own PRs automatically whereas a
  feature branch has to be rebased by hand. Rejected on the grounds above.
- **Risks & mitigations**: Dependency-tree changes could break the WIP Flow
  code. Mitigated by the required `quality` check running on every merged
  state, and by the M3 branch being rebased and re-linted the same day.

### Decision 2: Judge dependency PRs by the Security tab, not by PR type

- **What**: An initial reading claimed three PRs carried security advisories.
  That was wrong: the GHSA and CVE identifiers appeared inside upstream release
  notes embedded in the PR bodies, not in a Dependabot advisory block. All nine
  were routine version-update PRs — no `security` label, no advisory section.
  Merging them nonetheless closed 42 Dependabot alerts.
- **Why it matters**: PR type and security impact are independent. Inferring one
  from the other produced a confidently wrong answer in both directions —
  first overstating the security content, then understating it.
- **Follow-up**: Encoded in `.claude/rules/security.md`. The Security tab is the
  authoritative source; the PR list is not.

### Decision 3: Leave the ChromaDB alert open rather than dismiss it

- **What**: Dependabot alert #7 — `CVE-2026-45829` / `GHSA-f4j7-r4q5-qw2c`,
  a pre-authentication code-injection vulnerability in ChromaDB, rated Critical
  (CVSS 9.3). Affects `chromadb` 1.0.0–1.5.9; **no patched version exists**.
  It reaches this project as a transitive dependency of CrewAI. The decision is
  to leave the alert open and document the assessment, not to dismiss it.
- **Why**: The vulnerability requires a running ChromaDB server exposing its
  HTTP API. This project never starts one — neither `crew.py` nor `flow.py`
  enables CrewAI memory, and no knowledge or RAG sources are configured, so
  `chromadb` is installed but never instantiated. The code path is unreachable.
  However, that argument rests entirely on a configuration choice that a future
  milestone could flip, so dismissing the alert would hide a finding that may
  become valid.
- **Alternatives considered**: Dismiss as "vulnerable code not used" — rejected,
  because the dismissal would persist silently past the point where it stops
  being true. Upgrade — impossible, no fixed version is published.
- **Risks & mitigations**: Two future triggers must re-open this assessment:
  enabling CrewAI memory (plausible in M5+ for persona memory or performance
  tracking), and M4 deployment if a ChromaDB instance ends up network-reachable.
  Recorded here rather than in private notes because it is a dependency-tree
  fact derivable from the public `uv.lock`, not a live-deployment weakness.

### Decision 4: Least-privilege `permissions` for the CI workflow

- **What**: `ci.yml` now declares `permissions: contents: read` at workflow
  level. Resolves CodeQL alert #1 (`actions/missing-workflow-permissions`,
  CWE-275).
- **Why**: Without an explicit block, `GITHUB_TOKEN` inherits the repository
  default. The `quality` job only checks out the repo and runs ruff, mypy, and
  pytest — all read-only.
- **Risks & mitigations**: A future job needing write access will fail until it
  opts in at job level. That is the intended behaviour. The change went through
  a PR rather than a direct push because a malformed `ci.yml` blocks every merge
  in the repo.

### Decision 5: Move primary development to Claude Code running inside WSL

- **What**: Development moves from Claude Desktop / Cowork to the Claude Code
  VS Code extension running in WSL. Cowork keeps non-code work.
- **Why**: The deciding factor is verification. A cloud-sandboxed agent can edit
  files but cannot run the project's real toolchain — "it passes in my sandbox"
  does not mean "it passes in your WSL". Claude Code runs inside WSL against the
  same Python, the same `uv.lock`, and the same venv, so `make ci` produces the
  real answer. It also uses local git credentials, which removes the token-scope
  limitation encountered when editing workflow files.
- **Alternatives considered**: Connecting the WSL directory to Cowork over the
  Windows `\\wsl.localhost` path — rejected: slow 9P filesystem, permission and
  line-ending hazards, and above all a verification step running in the wrong
  environment.
- **Risks & mitigations**: Project knowledge that lived in the Claude Desktop
  project had to be ported, which is Decision 6.

### Decision 6: Split project context by load behaviour, not by topic

- **What**: The Claude Desktop project instructions (~150 lines) and shared
  collaboration conventions (~293 lines) were reduced and split across:
  `~/.claude/CLAUDE.md` (user scope, all projects), `CLAUDE.md` (this repo),
  `.claude/rules/*.md` (four path-scoped, one unconditional), and a git-ignored
  `CLAUDE.local.md` for machine and credential details.
- **Why**: CLAUDE.md files load in full every session and adherence degrades
  past roughly 200 lines. Roughly 443 always-loaded lines became ~286
  always-loaded plus ~213 loaded on demand.
- **Governing principle**: **triggers must be always-loaded; procedures can be
  on-demand.** A rule that fires in response to reading a file can be
  path-scoped. A rule that fires in response to a command, or that must be
  noticed during unrelated work, cannot be — it would never load.
- **Alternatives considered**: Copying everything verbatim into one CLAUDE.md —
  rejected on size. Putting ROADMAP and milestone state into CLAUDE.md —
  rejected, it would create a second source of truth; CLAUDE.md instructs the
  agent to read `docs/ROADMAP.md` instead.
- **Risks & mitigations**: CLAUDE.md is context, not enforcement, and the docs
  are explicit that adherence is not guaranteed. Hooks are the enforcement layer
  if one is ever needed; none are configured yet.

### Decision 7: The private archive repo is not named in the public repo

- **What**: `CLAUDE.md` and `.claude/rules/security.md` refer to "the private
  archive repo" by role only. Its identity and access method live in the
  git-ignored `CLAUDE.local.md`.
- **Why**: Avoids advertising private infrastructure. The practical risk is low
  — an outsider given the name still gets a 404 — but the habit is worth
  keeping.
- **Risks & mitigations**: An omitted name invites guessing. `CLAUDE.md`
  therefore states explicitly that if `CLAUDE.local.md` is absent the agent must
  ask rather than guess. `CLAUDE.local.md` does not travel with the repo, so a
  second machine will not have it — acceptable for a single-developer project.

### Decision 8: Teaching mode becomes a skill, without an enforcement hook

- **What**: The teaching-mode specification becomes
  `~/.claude/skills/teaching-mode/SKILL.md`, loaded on demand. The switch
  semantics stay in `~/.claude/CLAUDE.md`, always loaded.
- **Why**: Same seam as Decision 6 — the trigger must be recognised before the
  skill can be loaded, so the two cannot live in the same place.
- **Alternatives considered**: A `PreToolUse` hook denying `Edit`/`Write` under
  `src/**` and `tests/**` while the switch is on. This is the only mechanism
  that would actually enforce "let Stan write the code" rather than request it.
  Deferred deliberately: adding enforcement before observing the failure is
  solving an unproven problem.
- **Risks & mitigations**: The skill documents its own likely failure mode and
  names the hook as the escalation path.

## 2. System Changes

- `[Modify]` dependencies: nine transitive packages updated via `uv.lock` —
  `uv`, `urllib3`, `idna`, `mcp`, `pillow`, `python-multipart`, `cryptography`,
  `aiohttp`, `starlette`. Closed 42 Dependabot alerts.
- `[Modify]` `.github/workflows/ci.yml`: added workflow-level
  `permissions: contents: read`.
- `[Add]` `CLAUDE.md`: project context for Claude Code — session start-up
  procedure, repo layout, commands, git workflow, priorities, language policy.
- `[Add]` `.claude/rules/`: `security.md` (unconditional), plus `devlog.md`,
  `roadmap.md`, `python.md`, `github-actions.md` (path-scoped via `paths`
  frontmatter).
- `[Modify]` `.gitignore`: ignore `CLAUDE.local.md`.
- `[Modify]` `src/crewai_factory/flow.py` (on `feat/m3-flow-skeleton`): wrapped
  three over-length lines to satisfy ruff E501. No behaviour change.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Medium | `chromadb` `CVE-2026-45829`, Critical, no patched version, reached transitively via CrewAI | Open, assessed not reachable | Alert left open deliberately. Re-assess if CrewAI memory is enabled, or at M4 deployment. See Decision 3 |
| Medium | Dependabot **security updates** may not be enabled — only **alerts**. 42 alerts sat for ~2 weeks with no fix PRs; they were closed incidentally by routine version updates | Open | Verify the setting in repository security configuration and enable it. Inference from observed behaviour, not confirmed |
| Medium | mypy strict fails on `flow.py` with 5 errors: 4 from `Crew.kickoff()` returning `CrewOutput \| CrewStreamingOutput`, 1 from the empty-bodied `route_verdict` | Open | Narrow with `getattr` + `isinstance(EditorVerdict)`; the fifth resolves when `route_verdict` is implemented |
| Low | Feature branches do not trigger CI — `ci.yml` runs only on pushes to `main` and PRs targeting it. Lint errors written on 07-20/07-21 went undetected until 07-27 | Open | Open a draft PR early on feature branches |
| Low | The `minor-and-patch` group in `dependabot.yml` does not appear to apply to transitive lockfile updates, so they arrive as individual PRs | Open | Revisit the config before the next weekly batch. Inference, not verified against documentation |
| Low | `X_*` keys in `.env.example` are not validated at startup — `Settings` has no `X_*` fields and `extra="ignore"` drops unknown keys | Open | Resolves in M4 when the X client is built |

## 4. Milestones

- [ ] M3 DoD #1 — `@start` / `@listen` / `@router` replace `Process.sequential`
  - **Verification**: `ContentFlow` fully wired and `kickoff()` runs the loop.
  - **Status**: Pending — no change today. `route_verdict`, `save_post`, and
    `handle_failure` remain stubs.
- [x] Engineering foundation: dependency backlog cleared, CI permissions
  hardened, project context migrated to Claude Code
  - **Verification**: `main` at `c3ab2a3` contains all nine dependency updates,
    the `permissions` block, `CLAUDE.md`, and `.claude/rules/`; the `quality`
    check passed on each merged state; `.claude/rules/` confirmed present on
    `main` by re-fetching from the remote.
  - **Status**: Verified.

## 5. Learning Notes

### Commands / Code

- Command: `git fetch origin` versus `git pull`
  - Purpose: `fetch` updates remote-tracking references (`origin/main`) without
    touching any working branch. `pull` is `fetch` plus a merge into the current
    branch.
  - Key parameters: none, but the distinction is the point. A rebase workflow
    needs `fetch`; `pull` is only correct when the intent is genuinely to merge
    remote changes into the current branch.
  - Verification: `git log --oneline -10` after the operation.
  - Rollback: `git reflog` then `git reset --hard HEAD@{n}`.

- Command: `git push --force-with-lease`
  - Purpose: overwrite a remote branch after history has been rewritten by a
    rebase or reset.
  - Key parameters: with no argument it compares the remote against the
    remote-tracking ref from the last `fetch`, and refuses if someone else has
    pushed in the meantime. `--force` does not check.
  - Verification: re-fetch and confirm the remote SHA matches local.
  - Rollback: `git reflog` on the local branch, reset, force-push again.

- Command: `git mv rules .claude/rules`
  - Purpose: move a directory so git records a rename rather than five
    deletions plus five additions.
  - Verification: `git status` shows `renamed:` entries; blob SHAs are unchanged
    on the remote after pushing.

### Concepts / Architecture

- Concept: **`pull` after a rebase or reset silently undoes the work**
  - One-line explanation: after rewriting local history, the local branch
    diverges from — or falls behind — the remote, so `pull` merges or
    fast-forwards the old history straight back in.
  - Role in this project: hit twice today. The second case was the dangerous
    one: after `git reset --hard`, the local branch is strictly *behind* the
    remote, so `pull` fast-forwards cleanly with no conflict, no warning, and a
    success message — a complete silent revert. The rule is: after any history
    rewrite, the next remote operation is a push, never a pull.

- Concept: **Dependabot alerts and Dependabot security updates are separate
  settings**
  - One-line explanation: alerts detect vulnerabilities; security updates open
    PRs to fix them. Enabling only the first produces a growing alert list with
    no fix PRs.
  - Role in this project: explains why 42 alerts accumulated for two weeks and
    were then cleared incidentally by ordinary version bumps.

- Concept: **Assess a vulnerability by reachability, not severity**
  - One-line explanation: a Critical CVE in an installed package is irrelevant
    if the project cannot execute the vulnerable code path — but the reasoning
    must record what would make it reachable later.
  - Role in this project: the basis for leaving the ChromaDB alert open rather
    than dismissing it.

- Concept: **The `workflow` token scope is a deliberate boundary**
  - One-line explanation: modifying `.github/workflows/` requires a token with
    the `workflow` scope; without it the API returns
    `403 Resource not accessible`.
  - Role in this project: the scope exists so a general-purpose token cannot
    quietly rewrite CI — for example inserting a step that exfiltrates secrets.
    The correct response is to hand over a patch for manual commit, not to widen
    the token.

- Concept: **Triggers must be always-loaded; procedures can be on-demand**
  - One-line explanation: a path-scoped rule fires when Claude *reads* a
    matching file. Anything that fires from a typed command, or that must be
    noticed during unrelated work, will never load if it is path-scoped.
  - Role in this project: the first draft buried the `[CAUTION]` reflex and the
    `整理 devlog` / `進行當日總結` commands inside a rule scoped to
    `docs/devlog/**`. A pure coding session would never have loaded them, and
    the failure would have been silent. Fixed by moving all three triggers to
    `~/.claude/CLAUDE.md`.

### Working with an AI collaborator

Three misjudgements were caught by Stan today. Each is recorded because the
correction is more durable than the error.

1. **Momentum overrode a stated priority.** With "security > convenience"
   written in the instructions and visibly read, the first recommendation still
   followed the previous devlog's task order rather than a risk assessment.
   Written rules lose to momentum unless something forces the re-evaluation —
   here, Stan asking "why".
2. **A recommendation was given before the evidence was gathered.** The claim
   that three PRs carried security advisories was made before any PR body had
   been examined properly. Verification has to precede the recommendation, not
   follow the challenge.
3. **Decision-affecting information was placed after the action item.** A
   must-do fix was listed first and an "is this the right approach" question
   second, which guaranteed the fix would be executed before the question was
   read. Ordering should follow what changes the next action, not what feels
   most urgent.

An invented command (`make quality`, which is actually the CI *job* name; the
Makefile target is `make ci`) rounds out the list — asserted without reading the
Makefile.

## 6. Next Steps

- [ ] Reset `feat/m3-flow-skeleton` to `0b46cd4`, rebase onto `main` (`c3ab2a3`),
      force-push with lease. This drops the two migration commits, whose content
      is already on `main` via `#17`.
- [ ] Fix the four `union-attr` mypy errors in `edit_draft`: replace
      `result.pydantic` with `getattr(result, "pydantic", None)` followed by
      `isinstance(verdict, EditorVerdict)`, which narrows the type and fixes the
      downstream `verdict.score` / `verdict.feedback` errors in one change.
- [ ] Implement `route_verdict` (`@router`): compute
      `passed = verdict.score >= settings.quality_threshold`; return
      `"save"` / `"retry"` / `"failed"` from `len(attempts)` versus
      `max_attempts`. This also clears the fifth mypy error.
- [ ] Implement `save_post` and `handle_failure`; resolve whether `save_post`
      writes `verdict.final_post` or `self.state.post`.
- [ ] Rewire `crew.py` `run()` to kick off the Flow, preserving the `RunResult`
      contract.
- [ ] Integration tests with mocked Ollama: pass-first-try, retry-then-pass,
      cap-exhaustion.
- [ ] Verify whether Dependabot security updates are enabled; enable if not.
- [ ] Fill the `X API app` row in `CLAUDE.local.md` (locations only, never
      values).
- [ ] Open a draft PR for `feat/m3-flow-skeleton` so CI runs on every push.

## 7. Open Questions

- Does the `minor-and-patch` Dependabot group genuinely exclude transitive
  dependencies, or is something else producing individual PRs? Inferred from
  behaviour only.
- `final_post` semantics: does the editor still populate it, or does `save_post`
  use `self.state.post`? Carried over from 2026-07-21; decide when writing
  `save_post`.
- `output_pydantic` parse failure currently fails fast. Keep, or allow one
  bounded retry? Deferred until real-run failure-rate evidence exists.
- Should the one non-English string in the public rules — the `[CAUTION]`
  example in `.claude/rules/devlog.md` — stay in Traditional Chinese? It
  demonstrates conversational output, which the conventions specify is zh-TW.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-27

Latest progress:
  - Current phase: M3 (CrewAI Flow, retry-until-pass). No M3 feature progress
    today; the day went to engineering foundation work.
  - main is at c3ab2a3 and now contains: 9 transitive dependency updates
    (closing 42 Dependabot alerts), a least-privilege permissions block in
    ci.yml, and the Claude Code context migration (CLAUDE.md + .claude/rules/).
  - feat/m3-flow-skeleton is at 8173cef and needs cleanup: reset to 0b46cd4,
    then rebase onto c3ab2a3. The two commits being dropped are the Claude Code
    migration, already merged to main via PR #17.
  - flow.py passes ruff but fails mypy strict with 5 errors.

Current architecture summary:
  - Python 3.12 + CrewAI 1.15.2. The sequential pipeline in crew.py is untouched
    and still the active path; ContentFlow is being built beside it.
  - generate_topic (@start) -> write_draft (@listen(or_(generate_topic,
    "retry"))) -> edit_draft (@listen, output_pydantic=EditorVerdict) ->
    route_verdict (@router) -> save_post ("save") / handle_failure ("failed");
    the "retry" label loops back into write_draft.
  - route_verdict, save_post, handle_failure are still stubs; no end-to-end run.
  - Data flows only through self.state (ContentState: topic, post, verdict,
    max_attempts=3, attempts=list[Attempt]). Cycle count is len(attempts).
  - The quality gate is code-side: score >= Settings.quality_threshold (85).

Next steps:
  - Clean up the M3 branch (reset + rebase), then fix mypy, then write
    route_verdict / save_post / handle_failure.

For AI to be aware of:
  - Development is moving to Claude Code in WSL. CLAUDE.md and .claude/rules/
    are on main; ~/.claude/CLAUDE.md and the teaching-mode skill are user-scope
    and not in the repo.
  - Repo is PUBLIC; English-only engineering layer; never reference
    pre-public devlog IDs.
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only merges, auto-delete heads.
    Merging anything makes every other open PR stale.
  - Feature branches do NOT trigger CI. Open a draft PR to get coverage.
  - Confirm writes by re-fetching the remote, not by tool success messages.
  - After any history rewrite, the next remote operation is a push, never a
    pull.
  - chromadb CVE-2026-45829 (Critical, no fix) is open and assessed unreachable
    because CrewAI memory is not enabled. Re-assess if memory is turned on.
  - Technical failures fail fast (decision of 2026-07-20); best-attempt-on-
    failure on cap exhaustion (decision of 2026-07-20).
  - OLLAMA_MODEL default stays a cloud model (decision of 2026-07-16). Ollama
    runs as a separate service, not started by this repo.
```

---

## 9. ROADMAP Reconciliation

Required by the daily wrap-up. Each dimension gets an explicit conclusion.

### Milestone status — **no change**

M3 remains the current milestone and remains in progress. None of its five
definition-of-done items advanced today. `docs/ROADMAP.md` already describes M3
accurately; no edit needed. The TL;DR line "All M3 entry conditions met" is
still true.

### Backlog — **needs update**

Four candidate additions, none of which currently appear in §3 Backlog:

1. Verify and enable Dependabot security updates (repository setting).
2. Revisit `dependabot.yml` grouping — it does not appear to cover transitive
   lockfile updates.
3. Track `chromadb` `CVE-2026-45829`; re-assess when CrewAI memory is enabled or
   at M4 deployment. This is a genuine M4/M5 gate, not just housekeeping.
4. Adopt draft PRs on feature branches so CI runs before merge time.

Item 3 is the one worth pulling into a milestone rather than leaving in the
backlog, because it has a defined trigger condition rather than being
open-ended.

### Active Decisions Log — **no change**

Eight decisions were recorded today, but the Decisions Log threshold is
deliberately high: only decisions that change milestone structure or ordering
qualify. None do. The Claude Code migration changes the development environment,
not the roadmap. Recording it in the Decisions Log would dilute the table.

### Changelog — **needs update**

`main` changed materially today (dependencies, CI permissions, project context).
A single Changelog line is warranted, for example:
`2026-07-27: dependency sweep, CI least-privilege permissions, Claude Code
context migration`.

### Prior `[CAUTION]` follow-up

One `[CAUTION]` was raised today, concerning the nine-package dependency update
and the need to record it. Discharged by §2 of this devlog. No other outstanding
CAUTION lines.

---

*Draft — not yet written to the repository. Requires Stan's approval before
commit.*

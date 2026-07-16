# 2026-07-16: Land Dependabot, upgrade the dependency baseline, and harden the repository

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: Completed
**Related commits / PRs**: PR `#1` (dependabot config), PR `#2` (checkout v7), PR `#3` (setup-uv v7), PR `#4` (dependency group bump)

---

## TL;DR

All remaining go-public follow-ups are closed. Dependabot landed via the repo's first PR (`#1`) and immediately proved itself by opening three update PRs, all reviewed and merged: two major CI-action bumps (`#2`, `#3`) and one grouped dependency bump (`#4`: crewai 1.14.6 → 1.15.2, pytest 9.1.1, ruff 0.15.21, mypy 2.3.0). The upgraded stack was verified end-to-end with `make demo` — the run completed and reproduced the known M3 gap exactly as before (editor FAIL ends the run), confirming behavioral parity. The first CI run on `main` is green (README badge live). Repository-level hardening was completed: the Advanced Security suite is enabled and a branch ruleset now protects `main`. The `OLLAMA_MODEL` open question from the previous devlog is closed: keep the cloud-model default. Next session starts M3.

## 1. Decisions

### Decision 1: Keep the Ollama cloud model as the default `OLLAMA_MODEL`
- **What**: The default stays a cloud model; no config change, and no Backlog item is added for switching to a local default.
- **Why**: The development hardware cannot run a meaningfully capable local model, so a local default would break the project owner's own `make demo` — inverting the problem it was meant to solve. The residual risk (a first-time user without an Ollama account sees a failing demo) is already mitigated by the README Quick start note instructing users to set `OLLAMA_MODEL` to a model they have pulled.
- **Alternatives considered**: Switching the default to a small local model (raised in the previous devlog) — rejected for the reason above.
- **Risks & mitigations**: Slightly higher friction for first-time users → accepted; README note covers it. This closes the previous devlog's Open Question.

### Decision 2: Squash-only merge policy
- **What**: Repository settings allow only "Squash and merge"; merge commits and rebase-merges are disabled. Squash default message is set to the PR title. Head branches are auto-deleted after merge.
- **Why**: One PR = one commit on `main`, each pointing back to its PR via `(#N)`. Uniform history, no accidental merge-strategy mix-ups, and one less manual cleanup step.
- **Alternatives considered**: Keeping all three merge options — rejected: invites inconsistency for zero benefit on a solo project.
- **Risks & mitigations**: Squash discards intra-branch commit granularity → acceptable; fine-grained history rarely matters for small PRs, and the branch history remains visible in the PR.

### Decision 3: Protect `main` with a branch ruleset (solo-adapted)
- **What**: A ruleset on `main` enforces: required status check (`quality` CI job), branches must be up to date before merging, block force pushes, restrict deletions. Deliberately **not** enabled: "Require a pull request before merging" with required approvals.
- **Why**: Makes "green CI before merge" machine-enforced instead of self-discipline. "Up to date before merging" systematically prevents the stale-CI scenario observed today (a PR validated against an older `main`). Required approvals are omitted because GitHub does not allow self-approval — enabling it would deadlock a solo maintainer.
- **Alternatives considered**: Classic branch protection rules — rulesets are the current-generation mechanism; no reason to use the legacy one. Empty ruleset / no protection — rejected: `main` is the public face of the project.
- **Risks & mitigations**: Direct pushes to `main` are no longer possible, including docs-only edits — accepted as full GitHub Flow adoption; if the overhead proves painful for docs, a bypass can be revisited later (start strict, loosen on evidence).

### Decision 4: Enable the GitHub Advanced Security suite
- **What**: Enabled: Dependency graph, Dependabot alerts, Dependabot security updates, Grouped security updates, Private vulnerability reporting, CodeQL (default setup). Confirmed already active: Secret scanning + Push protection (public-repo defaults).
- **Why**: Free for public repos. Security updates are vulnerability-driven (immediate, CVE-triggered) and complement the weekly version updates from `dependabot.yml`. Push protection is a pre-commit guard against secret leaks, complementing the manual gitleaks workflow. CodeQL covers security patterns that ruff does not.
- **Risks & mitigations**: CodeQL adds a check per PR → negligible runtime at current codebase size.

## 2. System Changes

- `[Add]` **`.github/dependabot.yml`** (PR `#1`): weekly checks for the `uv` and `github-actions` ecosystems; minor/patch bumps grouped into a single PR, majors individual.
- `[Modify]` **CI workflow actions** (PRs `#2`, `#3`): `actions/checkout` 4 → 7, `astral-sh/setup-uv` 5 → 7. CI-infrastructure only; no code impact.
- `[Modify]` **Dependency baseline** (PR `#4`): crewai 1.14.6 → 1.15.2, pytest 9.0.3 → 9.1.1, ruff 0.15.15 → 0.15.21, mypy 2.1.0 → 2.3.0 (`pyproject.toml` + `uv.lock`). Branch was rebased onto latest `main` before merge so CI validated the exact merged combination.
- `[Modify]` **Repository settings** (not tracked in git — recorded here as the source of record):
  - Pull Requests: squash-only, PR-title default message, auto-delete head branches, always suggest updating PR branches.
  - Rules: `main` ruleset per Decision 3.
  - Advanced Security: suite enabled per Decision 4.
  - Actions workflow permissions: read-only.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | Repository settings (ruleset, security toggles, merge policy) live outside git; a repo rebuild would silently lose them | Open | This devlog section is the record; re-apply from here if ever needed |
| Low | With the ruleset active, docs-only changes also require the full branch → PR → CI cycle | Open | Accepted for now; revisit a bypass only if it becomes a real drag |

## 4. Milestones

- [x] **Dependabot operational + first CI run green on `main`**
  - **Verification**: PR `#1` merged; Dependabot opened PRs `#2`–`#4` within minutes (grouping behavior matches config: majors individual, minor/patch grouped); README CI badge green; Insights → Dependency graph → Dependabot shows both ecosystems checked.
  - **Status**: Verified
- [x] **Dependency baseline upgraded to pre-M3 latest and verified**
  - **Verification**: PR `#4` CI green after rebase onto latest `main`; local `uv sync` clean; `make demo` on crewai 1.15.2 ran the full strategist → writer → editor pipeline and produced a well-formed output file. The run ended with an editor FAIL verdict as final output — identical to pre-upgrade behavior and precisely the M3 motivation case, confirming behavioral parity.
  - **Status**: Verified
- [x] **Repository hardening applied**
  - **Verification**: Security tab shows Dependabot alerts / Code scanning / Secret scanning active; a test push directly to `main` is rejected by the ruleset.
  - **Status**: Verified

## 5. Learning Notes

### Commands / Code
- Command: `git fetch --prune`
  - Purpose: delete local remote-tracking refs (`remotes/origin/...`) whose remote branches no longer exist — the cleanup step after merged PRs.
  - Key parameters: `--prune` removes stale refs during the fetch.
  - Verification: `git branch -a` shows only `main` and `origin/main`.
  - Rollback: none needed (refs are re-fetchable).
  - **Lesson**: `git branch -d` manages *local* branches; `fetch --prune` manages *stale memories of remote* branches. Red `remotes/origin/...` entries are the latter — `-d` does not touch them.
- Command: `git branch -d` vs `-D` after a squash merge
  - **Lesson**: squash produces a *new* commit on `main`, so git may consider the source branch "not fully merged" and refuse `-d`. After confirming the content landed on the remote `main`, `-D` is safe and expected — not an error.
- Command: `@dependabot rebase` (PR comment)
  - Purpose: ask Dependabot to rebase its PR branch onto latest `main` and force-push; CI re-runs against the fresh combination.
  - Verification: a force-push event appears in the PR timeline; head SHA changes; checks re-run.

### Concepts / Architecture
- Concept: **Dependabot proposes, never disposes**
  - One-line explanation: every update is a PR gated by CI and human review; nothing merges itself, and `main` is untouched by ignored PRs.
  - Role in this project: made the "won't it break our pinned stack?" concern moot; Python version pins are out of Dependabot's scope entirely.
- Concept: **Stale-green CI on an outdated PR branch**
  - One-line explanation: a PR's green checks validate the merge result *as of when they ran*; after `main` moves, the tested combination no longer matches what merging would produce.
  - Role in this project: observed live on PR `#4` after merging `#2`/`#3`; now structurally prevented by the ruleset's "require branches to be up to date".
- Concept: **Dependabot rebases only on conflict**
  - One-line explanation: if the PR branch and `main` touch disjoint files, GitHub reports `mergeable_state: clean` and Dependabot leaves the branch alone; an explicit `@dependabot rebase` forces revalidation anyway.
- Concept: **CI must run secret-free**
  - One-line explanation: CI executes on GitHub's runners with no access to local `.env`; tests mock external calls, and any future CI secret belongs in Actions Secrets, never in the repo.
  - Role in this project: clarified that `.env` migration (local working copy) and CI health are fully independent concerns.
- Concept: **Version-update vs security-update Dependabot**
  - One-line explanation: `dependabot.yml` drives scheduled version bumps; security updates are alert-driven and fire immediately when a CVE with a patch appears — two separate mechanisms that complement each other.

## 6. Next Steps
- [ ] **Start M3**: CrewAI Flow skeleton (`@start` / `@listen` / `@router`), retry-until-pass, typed `EditorVerdict` — on crewai 1.15.2 as the baseline
- [ ] Adopt the new workflow reflex: every change (including docs) via branch → PR → green CI → squash merge
- [ ] When future Dependabot PRs arrive: majors individually reviewed; if a crewai major lands mid-M3, prefer deferring it until the Flow work is stable

## 7. Open Questions
- None. (The previous devlog's `OLLAMA_MODEL` question is closed by Decision 1.)

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-16
Latest progress:
  - Current phase: go-public follow-ups fully closed; M3 (CrewAI Flow) starts next session.
  - Completed: M1, M2, X API spike, pre-M3 hardening, go-public (2026-07-15),
    and today: Dependabot landed (PR #1), CI actions bumped (checkout v7, setup-uv v7),
    dependency baseline upgraded and demo-verified (crewai 1.15.2, pytest 9.1.1,
    ruff 0.15.21, mypy 2.3.0), first CI green on main, repo hardening
    (Advanced Security suite, main ruleset, squash-only merges).
  - In progress: nothing mid-flight.

Current architecture summary:
  - Python 3.12 + CrewAI 1.15.2 sequential pipeline (strategist → writer → editor),
    YAML personas, pydantic-settings config, loguru, pytest/ruff/mypy CI, uv.
  - Known accuracy note (unchanged, reconfirmed today on 1.15.2): an editor FAIL
    ends the run with the verdict as final output; the retry loop is M3's job.

Next steps:
  - M3: Flow skeleton with @start/@listen/@router, retry-until-pass (configurable cap),
    typed EditorVerdict (output_pydantic), router branches on typed fields only,
    integration tests with mocked Ollama, make demo shows observable retry.

For AI to be aware of:
  - This repo is PUBLIC; English-only engineering layer; never reference
    pre-public devlog IDs in public docs.
  - main is protected by a ruleset: no direct pushes (docs included); required
    status check `quality`; branches must be up to date before merging;
    squash-only merges; head branches auto-delete (run git fetch --prune locally).
  - Unresolved deployment security issues go to private notes (archive repo
    crewai-factory-docker), never the public repo; currently zero open items.
  - OLLAMA_MODEL default stays a cloud model by decision (2026-07-16); do not
    re-propose switching to a local default.
  - Dependabot: weekly, uv + github-actions, minor/patch grouped, majors
    individual. Majors need individual review; defer crewai majors mid-M3.
```

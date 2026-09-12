# 2026-09-12: Merge the dependabot backlog and re-plan M4 as M4a / M4b with two M5 feedback loops

> **This devlog is public.** Do not include: secrets or their fragments,
> internal hostnames/IPs, unresolved security issues of the live deployment,
> or personal context unrelated to the project. Security findings may be
> documented here **after** they are fixed; until then they belong in
> private notes.

**Status**: Completed
**Related commits / PRs**: `#24`, `#25` (dependabot, merged), ROADMAP v1.2 PR (this session)

---

## TL;DR
First session after a six-week pause. Cleared the two pending dependabot PRs
(crewai 1.15.14 → 1.15.16 group bump, types-pyyaml stub) — `make ci` green
(28 tests) and `make demo` shows the retry loop unchanged on the new crewai.
Then a planning pass on M4, which had grown too large: split it into **M4a**
(publish path verified on dev: deterministic guard → X client with `dry_run`
default and a SQLite ledger → CLI approval) and **M4b** (production
deployment with a private deployment repo, shadow mode for a week, then live).
Judge-hardening work was moved out of M4 entirely: with a human approval gate
in front of every post, editor drift cannot publish a bad post, and M4b's
shadow mode produces the calibration dataset for free. M5 was restructured
into an **inner loop** (M5a, editor score vs human verdict) and an **outer
loop** (M5b, per-post time-series metrics from X). Four decisions logged;
ROADMAP bumped to v1.2. No production code changed today.

## 1. Decisions

### Decision 1: Split M4 into M4a (publish path on dev) and M4b (production deployment)
- **What**: M4a builds and verifies the whole publish path on the dev machine
  (guard, X client, ledger, CLI approval, one live post from a test account).
  M4b deploys to the home server, runs in shadow mode ≥ 1 week, then goes live.
- **Why**: the original M4 bundled three deliverables with different risk
  profiles — the X client and review gate are testable on dev, deployment puts
  credentials on a server for the first time. Splitting makes "first real
  post" and "first credentials on the server" separate, individually
  reversible events, and each M4a PR is small enough to review in one sitting.
- **Alternatives considered**: keep M4 as one milestone with internal stages
  (as M3 did) — rejected: M3's stages shared one branch and one risk level;
  M4's do not.
- **Risks & mitigations**: two milestones means two wrap-ups and two ROADMAP
  passes — acceptable overhead; the entry conditions for M4b are written down
  so the boundary is explicit.

### Decision 2: Public engine repo ships templates only; account-specific configuration lives in a private deployment repo
- **What**: this repo stays a generic engine (code, demo personas, compose and
  systemd *templates*). A separate private repo holds real personas, the real
  compose override, the real timer schedule, and pins this repo by git tag or
  image tag. Secrets stay in the server's `.env`; the ledger DB and all metrics
  data stay on the server. Public devlogs, commits and README demos reference
  demo personas only.
- **Why**: the engine already treats personas as data (read-only volume) and
  keys as environment — nothing account-specific lives in code. Keeping it that
  way means the public portfolio repo never touches a real account, and
  upgrading the engine in production is a one-line tag change. This is the
  standard app-repo / config-repo split (Helm values, GitOps).
- **Alternatives considered**: (a) public fork — still public, and the fork
  relationship links the account to the portfolio; (b) private mirror of the
  code — two diverging codebases to keep in sync by hand; rejected.
- **Risks & mitigations**: leakage through devlogs / commit messages / README
  demos — mitigated by the standing §3.1-style rule that public docs reference
  demo personas only, and by the private repo not being named here.

### Decision 3: Move judge hardening out of M4 into M5a; split M5 into inner and outer loops
- **What**: measuring editor score stability and hardening `EditorVerdict`
  (temperature 0, rubric booleans, majority-of-3) become **M5a**. Audience
  metrics from X become **M5b**. M4 does neither.
- **Why**: the editor is one layer of a layered validation stack
  (deterministic rules → LLM judge → offline evals → shadow mode → human gate
  → post-deploy monitoring). With a human approval gate in front of every post,
  judge drift costs reading time but cannot publish a bad post, so it is not an
  M4 blocker. Hardening the judge is prompt iteration, which ROADMAP already
  defers past a stable pipeline. And M4b's shadow mode yields 20–30 real drafts
  with editor score + human verdict — a better calibration set than any
  synthetic probe, at zero extra cost. Neither cost moves by deferring: judge
  probes call only the Ollama backend (not the X API), and the code change is
  the same size later.
- **Alternatives considered**: run a judge-stability probe and rubric rewrite
  first (v1 of the plan) — rejected as M5 work smuggled into M4; kept as an
  optional, dependency-free spike (`scripts/evals/judge_probe.py`).
- **Risks & mitigations**: the 85 threshold may be partly random until M5a —
  acceptable while every post is human-approved.

### Decision 4: Ledger is SQLite, not jsonl
- **What**: `ledger.py` uses stdlib `sqlite3`, one file, a `posts` table in
  M4a; `metrics_snapshots` joins on `tweet_id` in M5b. `posts` columns are
  proposed in ROADMAP but **not yet reviewed** — finalised at PR 2 kickoff.
- **Why**: the publish flow needs an *update* (fill in `tweet_id` after
  posting), M5b needs a second table and joins, and two processes (publisher,
  metrics collector) may write concurrently. jsonl is append-only, untyped,
  and needs a full rewrite for any update; SQLite handles all three with no
  extra dependency and reads straight into pandas.
- **Alternatives considered**: jsonl — the honest choice if the ledger were
  only ever appended and eyeballed; the stated M5b requirements rule that out.
- **Risks & mitigations**: binary file, schema migrations — mitigated by
  keeping the M4a schema minimal and not pre-building M5 columns.

## 2. System Changes
- `[Modify]` **dependencies (`uv.lock`)**: crewai 1.15.14 → 1.15.16,
  python-dotenv 1.2.2 → 1.2.3, ruff 0.16.2 → 0.16.3, mypy 2.3.0 → 2.3.1 (#24);
  types-pyyaml stub bump (#25). Lock-only; `pyproject.toml` floors unchanged.
- `[Modify]` **`docs/ROADMAP.md` → v1.2**: M4 → M4a / M4b; M5 → M5a / M5b /
  M5c; Backlog refreshed; four Decisions Log rows; Changelog entry.
- No source code changed.

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | crewai 1.15.16 emits 42 `DeprecationWarning`s in tests (`function_calling_llm`, `allow_code_execution`, `reasoning`) — none used by this project | Open (observed) | Leave visible; review release notes carefully on the next crewai major bump. Do not blanket-filter warnings yet |
| Low | crewai 1.15.15/16 added tracing/telemetry logic; no telemetry setting exists in this repo (defaults apply) | Open | Decide and document in M4b (outbound-connection inventory) |
| Low | `types-pyyaml` arrives as a separate dependabot PR because its 4-part version does not match the `minor-and-patch` group | Open | Backlog: add a `types-*` pattern to the group |
| Low | `persona.max_length = 280` ignores X's weighted counting (CJK = 2, URL = 23); a zh-TW persona effectively has 140 | Open | M4a PR 1 redefines `max_length` as X weighted units and enforces it in the guard |
| Low | Demo personas' editor backstory still ends with a free-text `Format: "Score: XX \| Verdict: …"` line that contradicts the structured `EditorVerdict` | Open | Remove in M5a |
| Low | `X_*` keys in `.env.example` still unvalidated (`Settings` has no `X_*` fields) — carried from 2026-07-27 | Open | M4a PR 2 |

## 4. Milestones
- [x] **Dependabot backlog cleared** — #24 and #25 merged; only `main` remains
  - **Verification**: remote re-fetched: `main` at `2cc2a92`, no dependabot
    branches; local `make ci` green (ruff, format, mypy, 28 tests);
    `make demo` run shows `Attempt n/3 — score` and router lines as in the
    2026-07-31 baseline
  - **Status**: Verified
- [x] **M4a entry condition met** — `main` green, dependencies current
  - **Verification**: same as above
  - **Status**: Verified
- [ ] **ROADMAP v1.2 merged** — this session's PR
  - **Verification**: re-fetch `main` and confirm `docs/ROADMAP.md` header
    reads `v1.2` and the file ends with `*End of Roadmap v1.2*`
  - **Status**: Pending

## 5. Learning Notes

### Commands / Code
- Command: `git fetch --all --prune && git branch -r`
  - Purpose: see what actually exists on the remote after merges
    (dependabot branches auto-delete; a stale local view lies)
  - Key parameters: `--prune` drops remote-tracking refs that no longer exist
  - Verification: only `origin/main` listed after both merges
  - Rollback: read-only
- Command: `git merge-base --is-ancestor origin/main <branch>`
  - Purpose: answer "is this branch based on current main?" without opening
    the PR page
  - Key parameters: exits 0 if the first ref is an ancestor of the second
  - Verification: both dependabot branches reported YES before merging
  - Rollback: read-only
- Concept: **"Head branch was modified" after Update branch**
  - Dependabot rebases its own PR branch as soon as the base moves; the GitHub
    merge box then reports the head changed. It is a stale-page notice, not a
    failure — reload, wait for CI on the new head, merge.

### Concepts / Architecture
- Concept: **Layered validation for LLM applications**
  - One-line explanation: deterministic rules → LLM judge → offline evals →
    shadow mode → human gate → post-deploy monitoring, cheapest and most
    stable first.
  - Role in this project: M4a builds the deterministic layer and the human
    gate; M4b adds shadow mode; M5a calibrates the judge; M5b adds monitoring.
- Concept: **Inner loop vs outer loop**
  - One-line explanation: inner loop asks "does the judge agree with me?"
    (pre-publish, hours); outer loop asks "does the audience respond?"
    (post-publish, days).
  - Role in this project: M5a and M5b respectively; they need different data
    (ledger verdicts vs X `public_metrics`) and different cadences.
- Concept: **Shadow mode / dry-run deployment**
  - One-line explanation: deploy the real thing with the side effect switched
    off; verify plumbing and content separately before flipping live.
  - Role in this project: M4b runs the timer for a week with
    `publish_mode=dry_run`, and the human's daily approve/reject becomes M5a's
    dataset.
- Concept: **App repo vs config/deployment repo**
  - One-line explanation: code is generic and public; what makes it *your*
    deployment (personas, schedule, overrides) is configuration kept apart.
  - Role in this project: public engine repo + private deployment repo
    (Decision 2); same idea as Helm chart vs values, or GitOps.
- Concept: **X weighted character count**
  - One-line explanation: X counts CJK characters as 2 and any URL as 23
    toward the 280 limit.
  - Role in this project: `max_length` becomes "X weighted units"; the guard
    enforces it (M4a PR 1).
- Concept: **SQLite vs jsonl for a ledger**
  - One-line explanation: jsonl is an append-only log; SQLite is a one-file
    database with updates, joins, types and locking, no extra dependency.
  - Role in this project: Decision 4.

## 6. Next Steps
- [ ] Merge the ROADMAP v1.2 PR; re-fetch to verify (§5.2 rule)
- [ ] M4a PR 1 — deterministic guard (`guard.py` + tests; `max_length`
  semantics documented in the persona schema)
- [ ] M4a PR 2 — X client, `publish_mode`, SQLite ledger; **review and
  finalise the `posts` columns at kickoff**
- [ ] M4a PR 3 — CLI `publish`; one live post from a test account
- [ ] Before M4b: set up a non-sensitive test X account with its own developer
  app (read + write scopes)
- [ ] Backlog, any time: remove migration dead code; `dependabot.yml` `types-*`
  pattern
- [ ] Optional spike: `scripts/evals/judge_probe.py`

## 7. Open Questions
- Telegram approval bot (polling `getUpdates`, outbound only): M4b stretch or
  M5? Decide after M4a PR 3 shows how painful CLI approval is over SSH.
- X API read pricing and `non_public_metrics` availability for M5b — verify
  against current docs at M5b start.
- How the outer loop should feed back into agents (prompt edits, persona
  edits, few-shot examples of top performers) — deliberately undecided until
  the time-series curves are visible.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-09-12
Latest progress:
  - Current phase: M4a (publish path on dev) — entry condition met, no
    code started. ROADMAP v1.2 written this session (PR pending/merged —
    verify by re-fetching main).
  - Completed today: dependabot #24 (crewai 1.15.16 group) and #25
    (types-pyyaml) merged; make ci green (28 tests); make demo retry loop
    verified on crewai 1.15.16. M4 re-planned (see Decisions 1–4).
  - In progress: nothing mid-flight.

Current architecture summary (unchanged code since 2026-07-31):
  - Python 3.12 + CrewAI 1.15.16. crew.run() -> ContentFlow:
    generate_topic (@start) -> write_draft (@listen(or_(generate_topic,
    "retry"))) -> edit_draft (@listen, output_pydantic=EditorVerdict) ->
    route_verdict (@router: save/retry/failed) -> save_output /
    handle_failure. Gate is code-side: score >= Settings.quality_threshold
    (default 85). Only a stderr loguru sink.
  - No guard layer, no X client, no ledger yet — these are M4a PRs 1–3.
  - Settings has NO X_* fields (extra="ignore" drops them) — M4a PR 2.
  - build_tasks + sequential-Crew helpers are dead code (backlog removal).

Next steps (M4a, three PRs, in order):
  1. guard.py — 3 rules (X weighted length, placeholders, dedupe vs ledger),
     runs inside edit_draft before the editor crew; synthesises
     EditorVerdict(score=0) on violation. Also runs before live publish.
  2. x_client.py + Settings X_* (SecretStr) + publish_mode (default
     dry_run) + ledger.py (SQLite, table `posts`; columns PROPOSED in
     ROADMAP, NOT YET REVIEWED — discuss at kickoff).
  3. CLI `publish <draft.md>`: re-run guard, post, update ledger row.
     Publishing lives OUTSIDE the Flow. DoD: one live post from dev using
     a demo persona and a non-sensitive TEST account.
  Then M4b: private deployment repo, prod compose, systemd timer, file-log
  sink, telemetry decision, chromadb CVE re-assess, shadow mode >= 1 week.

For AI to be aware of:
  - Repo is PUBLIC; English-only engineering layer; never reference
    pre-public devlog IDs; never name the production host, the private
    deployment repo, or any non-demo persona in public docs/commits.
  - Public engine repo ships TEMPLATES only; account-specific config,
    personas, ledger DB and metrics live in a private deployment repo / on
    the server (Decision 2, 2026-09-12).
  - main is ruleset-protected: no direct pushes, required check `quality`,
    branches must be up to date, squash-only, auto-delete heads. Confirm
    writes by re-fetching the remote, not by tool success messages.
  - Code work runs in Claude Code inside WSL (make ci uses the real env);
    Cowork handles non-code work and reads a cloud clone of the public repo
    (no GitHub write access from Cowork; Stan pushes).
  - Dev machines: two WSL2 laptops (Ubuntu 22.04 and 24.04) — if something
    runs on one and not the other, suspect the distro/version gap first.
  - Judge hardening is M5a, NOT M4. Do not re-add it to M4a scope.
  - Ledger is SQLite. `posts` columns are a proposal pending review.
  - crewai 1.15.16 emits DeprecationWarnings for fields this project does
    not use; do not filter them yet; read release notes carefully on the
    next crewai major.
  - TEACHING MODE (教學模式): OFF this session (planning only). Per-session
    toggle Stan controls — wait for Stan to set it.
  - Unresolved deployment security issues go to private notes; last known
    state (2026-07-31) was zero open items — Cowork cannot read the private
    repo, so re-confirm with Stan at M4b entry.
```

---

## 9. ROADMAP Reconciliation

### Milestone status — **updated in v1.2 (this session)**
M3 unchanged (complete). M4 replaced by M4a 🔨 (entry condition met, current)
and M4b 📋 (entry conditions listed). M5 replaced by M5a / M5b / M5c. TL;DR
points at M4a.

### Backlog — **updated in v1.2**
Removed: "home server VPN stability" and "compose dev/prod separation" (now
M4b entry condition / plan items); "file-log sink" (M4b plan). Added:
`dependabot.yml` `types-*` pattern; crewai deprecation-warning watch. Persona
strategy reframed as a private-deployment concern. Carried: dead-code
removal, Dependabot security updates, chromadb CVE, draft PRs, README demo.

### Decisions Log — **updated in v1.2**
Four rows added (M4 split; public/private repo split; judge hardening → M5a
and M5 loop split; SQLite ledger). All four change milestone structure or a
security boundary, so they meet the log's threshold.

### Changelog — **updated in v1.2**
v1.2 line added. Lands on `main` when the ROADMAP PR merges.

### Earlier `[CAUTION]` items — all accounted for
- M4a/M4b split → Decision 1, ROADMAP Decisions Log row 11
- Public/private repo split → Decision 2, ROADMAP Decisions Log row 12
- M5 two-loop clarification → Decision 3, ROADMAP Decisions Log row 13

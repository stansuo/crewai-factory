# 2026-07-15: Take the project public as `crewai-factory` with a fresh history

**Status**: Completed
**Related commits / PRs**: `crewai-factory` initial commit `ee7dea5`; private archive repo commit `b63dd84`

---

## TL;DR

The project went public today, and this devlog is the public repo's first entry. A fresh repo `crewai-factory` was created from a sanitized export of the private working repo (`git archive`, tracked files only), with git history starting at the go-public snapshot. Before publishing, a dual-track secrets scan (per-file semantic review + local gitleaks) confirmed zero leaks; all documentation was rewritten to public standard (English-only engineering layer, no internal references). The old private repo was converted into an archive. Post-push, every file on the new remote was verified — unchanged files by blob-SHA comparison, changed files by full re-read.

## 1. Decisions

### Decision 1: Start clean — fresh history for the public repo
- **What**: The public repo begins with a single initial commit; public devlogs begin with this entry. Pre-public history (all prior devlogs, decisions, experiments) stays in the private archive repo.
- **Why**: Guarantees the public history contains nothing unintended, with zero reliance on history-rewriting tools. Simplest possible audit surface: one commit, fully scanned.
- **Alternatives considered**: Migrating history with `git filter-repo` — rejected: rewriting is error-prone, and residue is hard to prove absent. Publishing the existing repo directly — rejected for the same auditability reason.
- **Risks & mitigations**: Loss of visible project history on the public side → mitigated by the private archive remaining fully intact, and by this ROADMAP summarizing completed milestones.

### Decision 2: All-English repository policy
- **What**: The engineering layer (code comments, docs, config comments, devlogs) is English-only. Deliberate multilingual *content* (e.g. the zh-TW `travel-storyteller` persona) is exempt — it is a feature, not a comment.
- **Why**: Recruiter-friendly for an international audience; doubles as deliberate English writing practice.
- **Alternatives considered**: Bilingual docs — rejected as double maintenance cost.
- **Risks & mitigations**: Slower writing at first → accepted as a feature (learning goal).

### Decision 3: Two-tier documentation — public repo + private notes
- **What**: This repo's `docs/devlog/` is the single source of truth for project history. The private archive repo holds a private-notes area for content that must not be public: unresolved security issues of the live deployment, internal network details, and sensitive deployment specifics. Lifecycle rule: a security finding moves to the public devlog only **after** it is fixed.
- **Why**: Keeps public devlogs honest without turning them into a reconnaissance aid; private notes stay versioned and AI-readable instead of scattered local files.
- **Alternatives considered**: A third dedicated notes repo — rejected: management overhead for low expected volume. Local/Drive notes — rejected: no versioning, poor AI access.
- **Risks & mitigations**: Two live repos could blur which one is active → mitigated by a prominent archive notice in the old repo's README.

### Decision 4: Spike scripts read credentials from the environment
- **What**: `scripts/spikes/test_x_api_{get,post}.py` now load `X_*` variables via `python-dotenv` / `os.getenv()` with fail-fast validation, replacing paste-in placeholder constants.
- **Why**: Aligns the scripts with their own README's "never hardcode keys" rule; reuses the same variable names as `.env.example`, so one `.env` serves both spikes and the future M4 client.
- **Alternatives considered**: Keep placeholders (status quo) — rejected: a public repo should model the practice it preaches.
- **Risks & mitigations**: `requests-oauthlib` is not a project dependency → documented in the spikes README (`uv pip install`, re-install after `uv sync`).

### Decision 5: Keep the Issues & Risks section in public devlogs
- **What**: The devlog template retains §3 (Issues & Risks) with an inline gate note: technical debt and design risks are recorded openly; unresolved deployment security issues stay private until fixed.
- **Why**: Openly tracked risks demonstrate engineering maturity; only reconnaissance value must be withheld.

## 2. System Changes

- `[Add]` **`crewai-factory` (this repo)**: initial commit from sanitized export; the active development repo from now on.
- `[Modify]` **README**: broken ASCII pipeline diagram → Mermaid (native GitHub rendering); FAIL branch drawn as a dashed edge labeled "retry loop lands in M3" (accuracy: retry does not exist yet); CI badge added; "runs 100% locally" reworded to reflect the Ollama-cloud default model; Quick start warns to set `OLLAMA_MODEL` to a pulled model.
- `[Modify]` **`scripts/spikes/`**: env-var credential loading (Decision 4); README gains Running instructions.
- `[Modify]` **`docs/devlog/_DEVLOG_TEMPLATE.md`**: public-repo gate notice at top; §3 inline security rule; project-relevant filename example.
- `[Modify]` **`.gitignore`**: comments translated to English; rules unchanged.
- `[Modify]` **private archive repo**: README archive notice; private-notes area created (commit `b63dd84`).

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Low | `.github/dependabot.yml` missing — was on the go-public prep list but dropped during checklist consolidation | Open | Add via PR next session (uv + github-actions ecosystems) |
| Medium | Default `OLLAMA_MODEL` is an Ollama **cloud** model → a first-time user's `make demo` fails without an Ollama account | Open | Consider switching the default to a small local model (touches `config.py`, `test_config.py`, `.env.example`); decide before/with M3 |
| Low | CI badge shows no status until the first Actions run completes | Open | Check the Actions tab next session |

## 4. Milestones

- [x] **Go-public: fresh repo `crewai-factory` published**
  - **Verification**: dual-track secrets scan clean (per-file semantic review + local `gitleaks dir`, only local `.env` hits as expected); `git ls-files` confirms `.env` untracked; CJK-character grep clean except deliberate persona content; post-push remote verification — unchanged files bit-identical by blob SHA, changed files re-read in full; no `.env` in the public tree; default branch `main`.
  - **Status**: Verified

## 5. Learning Notes

### Commands / Code
- Command: `gitleaks dir . --verbose --redact`
  - Purpose: scan working-tree files for secret patterns (v8.19+ syntax; `detect --no-git` is legacy).
  - Key parameters: `dir` scans files including untracked ones (no git history); `--redact` masks matched secrets in output.
  - Verification: expected hits only in local `.env`; anything else is a finding.
  - Rollback: read-only, none needed.
  - **Lesson**: always default to `--redact` when a scan is expected to hit real secrets — printing keys to a terminal violates "don't display secrets unnecessarily", even locally.
- Note: **if secrets do get printed to a terminal** — local display is not a leak; no key rotation needed. Close the tab or clear the buffer + scrollback (Windows Terminal: `Ctrl+Shift+P` → Clear buffer). Shell history is only a concern if keys were *typed*, not printed.
- Command: `git archive HEAD | tar -x -C <target>`
  - Purpose: export **tracked files only** — untracked files (`.env`, IDE junk) can never ride along, unlike `cp -r`. The safe way to seed a public repo.
  - Verification: target has no `.git`, no `.env`; `find <target> -name '.env*'` lists only `.env.example`.
  - Rollback: delete the target directory; the source repo is untouched.
- Command: `git branch -M main` (after first commit, before first push)
  - Purpose: `git init` still defaults to `master` unless `init.defaultBranch` is set; without the rename, `push -u origin main` fails with "src refspec main does not match any".
  - Key parameters: `-M` = force-rename the current branch.
  - Verification: `git branch --show-current` → `main`.
  - Note: `git config --global init.defaultBranch main` makes this permanent.
- Command: `grep -rn -P '[\x{4e00}-\x{9fff}]' . -l`
  - Purpose: find files containing CJK characters (Unicode range match) — quick audit for an English-only policy.
- Command: `uv pip install <pkg>` vs `uv add` vs `uv sync`
  - `uv pip install`: installs into the project `.venv`, **not** recorded in `pyproject.toml` / `uv.lock`.
  - `uv sync`: makes the venv **exactly equal** to the lockfile — it also removes anything not in it (unlike pip's install-only semantics). Ad-hoc packages vanish on the next sync; a feature for spike deps, a surprise if unexpected. `--inexact` disables removal (avoid: it sacrifices reproducibility).

### Concepts / Architecture
- Concept: **Start clean vs. history rewriting**
  - One-line explanation: when publishing a repo with a private past, exporting a verified snapshot beats rewriting history — absence of residue is provable by construction.
  - Role in this project: the foundation of today's go-public approach.
- Concept: **Blob-SHA verification**
  - One-line explanation: identical git blob/tree SHAs guarantee bit-identical content — comparing SHAs against the source verifies an export without re-reading every file.
  - Role in this project: how the post-push per-file verification was done efficiently.
- Concept: **GitHub alert syntax** (`> [!IMPORTANT]`)
  - One-line explanation: renders as a highlighted callout box on GitHub — used for the archive notice.
- Process lesson: a checklist item (dependabot) was silently dropped while consolidating lists mid-session. Before executing a multi-step plan, re-diff the current checklist against its earliest version.

## 6. Next Steps
- [ ] `.github/dependabot.yml` via PR (uv + github-actions ecosystems) — first pull-request exercise on this repo
- [ ] Confirm the first CI run is green (Actions tab); the README badge should turn green
- [ ] Decide on switching the default `OLLAMA_MODEL` to a local model (see Issues); add a Backlog line to the ROADMAP
- [ ] Close out the archive repo: freeze banner on its ROADMAP + a final pointer devlog
- [ ] Then: start M3 (Flow skeleton)

## 7. Open Questions
- Default model: switch to a small local model before M3, or fold the change into M3's PR?

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-07-15
Latest progress:
  - Current phase: went PUBLIC today (repo stansuo/crewai-factory, initial commit ee7dea5,
    fresh history; this devlog is the repo's first). Old private repo = archive + private notes.
  - Completed: M1, M2, X API spike, pre-M3 hardening, go-public (sanitization + dual-track
    secrets scan + post-push per-file remote verification, all clean).
  - In progress: nothing mid-flight; next session starts with the dependabot PR + CI green check.

Current architecture summary:
  - Python 3.12 + CrewAI sequential pipeline (strategist → writer → editor), YAML personas,
    pydantic-settings config, loguru, pytest/ruff/mypy CI, Docker multi-stage, uv.
  - Known accuracy note: an editor FAIL currently ends the run with the verdict as output;
    the retry loop is M3's job (README diagram shows it as a dashed "lands in M3" edge).

Next steps:
  - dependabot.yml PR (uv + github-actions), verify first CI run green
  - Decide default OLLAMA_MODEL → local model (default is a cloud model; a first-time user's
    make demo fails). Touches config.py, test_config.py, .env.example.
  - Archive-repo closeout (ROADMAP freeze banner + pointer devlog).
  - Then M3: CrewAI Flow (@start/@listen/@router), retry-until-pass, typed EditorVerdict.

For AI to be aware of:
  - This repo is PUBLIC. Everything committed is world-readable. English-only engineering layer.
  - Unresolved deployment security issues go to private notes (archive repo), never here;
    document them publicly only after they are fixed.
  - Never reference pre-public devlog IDs in public docs (dead references by design).
  - Secrets-scanning commands: default to redacted output. gitleaks v8.19+: use `gitleaks dir`.
```

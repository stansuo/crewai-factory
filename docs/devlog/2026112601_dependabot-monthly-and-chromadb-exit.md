# 2026-11-26: Clear the Dependabot queue, move version updates to monthly, and see chromadb leave the dependency tree

**Status**: Completed
**Related commits / PRs**: `#51` (`bd78b12`), `#52` (`e83125d`), `#53` (`3619e68`), `#55` (`721147c`), `#54` (`a277604`)

---

## TL;DR
The project had been idle for 13 days since the 2026-11-13 sweep. A status
check found `main` green and M4a still not started, plus two open Dependabot
PRs. Both were merged, along with three more that arrived during the session.
Version updates now run monthly instead of weekly (#53), so the queue no longer
outruns the work. The `github-actions` rule's stale explanation of Dependabot
grouping was corrected in the same PR. The most consequential change arrived
incidentally: crewai 1.15.44 (#54) made chromadb an optional extra, so chromadb
left `uv.lock`. All four open Dependabot alerts were chromadb alerts with no
patched version. The `type-stubs` group added in #47 did not catch the next
`types-*` release (#55). No application code changed. M4a PR 1 (`guard.py`) is
still next.

## 1. Decisions

### Decision 1: Version updates monthly instead of weekly
- **What**: `.github/dependabot.yml` sets `interval: "monthly"` for both the
  `uv` and `github-actions` ecosystems (#53).
- **Why**: Every pause in this project has ended with a queue of Dependabot
  PRs to clear before any feature work. `main` requires branches to be up to
  date, so each merge makes every other open PR stale and costs another CI
  cycle. Since 2026-09-12, two sessions have gone entirely to dependency
  maintenance, and M4a has not started.
- **Alternatives considered**: (a) keep `weekly`. Rejected for the reason
  above. (b) auto-merge patch updates. Rejected because crewai patch releases
  change behaviour (1.15.41 alone adds a URL-host feature, and 1.15.44 changes
  the dependency tree, see Decision 3), and the project's priorities put
  "never break a working state" above convenience.
- **Risks & mitigations**: A monthly interval does not delay security fixes.
  The Dependabot options reference describes `schedule.interval` as defining
  "whether to look for version updates", and the security-updates page says
  that when security updates are enabled, Dependabot "will automatically try
  to open pull requests to resolve every open Dependabot alert that has an
  available patch". Security updates are triggered by alerts, not by the
  schedule. Observed evidence agrees: #51, a security update, arrived on its
  own on 2026-11-15, outside the weekly batch. The docs were first unreachable
  from the cloud session; they were read after Stan widened its network
  access.

### Decision 2: Merge the security update first, then the grouped updates one at a time
- **What**: #51 (security), then #52 after update-branch and green CI, then
  #53, #55 and #54, each updated and re-verified against the new `main`.
- **Why**: The remaining PRs were few, so merging them one at a time cost
  little. Unlike the 14 PRs on 2026-11-13, consolidating them into one lockfile
  bump would not have saved anything. The security update went first so it
  would not wait behind the others.
- **Alternatives considered**: One consolidated lockfile bump as in #46.
  Rejected because the batch was too small to need it.
- **Risks & mitigations**: None beyond normal CI; `make ci` was also run
  locally on the final `main`.

### Decision 3: Leave chromadb alerts to close on their own; do not dismiss
- **What**: No action was taken on the four chromadb alerts (#7, #48, #49,
  #50). They should resolve automatically now that chromadb is out of
  `uv.lock`.
- **Why**: The security rule prefers leaving an alert open over dismissing it
  when a "not affected" argument rests on a setting that could change. Before
  #54, the argument was "CrewAI memory is off", which is exactly that kind of
  setting. After #54, the package is not installed at all. That is a stronger
  reason, and GitHub will record the alerts as fixed rather than dismissed.
- **Alternatives considered**: Dismiss as "vulnerable code not used".
  Rejected: it would have rested on the memory setting, and it is unnecessary
  now.
- **Risks & mitigations**: The alerts come back if chromadb returns, and there
  is no patched version (see Issues & Risks).

## 2. System Changes
- `[Modify]` `.github/dependabot.yml`: version-update interval `weekly` →
  `monthly` for `uv` and `github-actions` (#53).
- `[Modify]` `.claude/rules/github-actions.md`: Dependabot section now
  separates version updates (follow `dependabot.yml`) from security updates
  (alert-driven, not batched by groups), replacing the earlier guess that
  "grouping applies to direct dependencies only" (#53).
- `[Modify]` `uv.lock`, direct dependencies: crewai 1.15.34 → 1.15.41 (#52) →
  1.15.44 (#54); loguru 0.7.3 → 0.8.0, pydantic-settings 2.16.2 → 2.16.3
  (#52); ruff 0.17.3 → 0.17.5 (#52) → 0.17.6 (#54); types-pyyaml
  6.0.12.20260906 → 6.0.12.20261122 (#55). Transitive: opentelemetry-api
  1.45.1 → 1.45.2 (#51, security update).
- `[Remove]` chromadb and its subtree from `uv.lock` (#54). crewai 1.15.44
  declares `chromadb~=1.5.9; extra == 'chromadb'`, so chromadb is now an
  optional extra. Removed with it: kubernetes, onnxruntime,
  `requests-oauthlib`, bcrypt, the OTLP gRPC exporter, uvloop, and others.
  `uv.lock` went from about 152 packages to 135. `qdrant-client` 1.14.3 is new,
  a direct dependency of crewai.
- `[Modify]` `.github/dependabot.yml` comment and `.claude/rules/github-actions.md`:
  replaced the "not yet checked against the docs" wording with what the
  Dependabot docs actually say, and recorded the `type-stubs` gap (this
  devlog's PR).

## 3. Issues & Risks

| Severity | Description | Status | Mitigation / Next Step |
|---|---|---|---|
| Medium | `scripts/spikes/test_x_api_{get,post}.py` import `requests_oauthlib`, which was never a declared dependency and arrived only via chromadb → kubernetes. #54 removed it, so the spikes now fail with `ImportError`. M4b entry condition 3 re-verifies credentials with `test_x_api_get.py` | Open | M4a PR 2 chooses and declares the OAuth 1.0a client library. The spikes should use the same library. Until then, running a spike needs `uv run --with requests-oauthlib` |
| Medium | Four chromadb alerts, all with **Patched version: None** for `>= 1.0.0, <= 1.5.9`. The two critical ones are code injection on the Chroma **HTTP server**: CVE-2026-45829 (#7, pre-auth, `POST …/collections`) and CVE-2026-45833 (#50, needs `UPDATE_COLLECTION`). Both work by making the server load a model repository with `trust_remote_code=true`. #49 (CVE-2026-45830) and #48 (CVE-2026-45831) are cross-tenant authorisation flaws in the server's auth layer (`SimpleRBACAuthorizationProvider`). Details read from the GitHub alerts and OSV | Resolved by removal (pending confirmation) | Not reachable before #54 either: this project never runs a Chroma server and does not enable CrewAI memory, knowledge or RAG. Becomes reachable if a Chroma server is run on any network, or `crewai[chromadb]` is installed and fed untrusted collection configuration. Confirm in the Security tab that the alerts closed after the dependency graph refresh |
| Low | The `type-stubs` group (#47) did not apply: the next stub release arrived as an individual PR (#55). Confirmed by the branch name `dependabot/uv/types-pyyaml-6.0.12.20261122`: per the options reference, solo updates name the branch after the dependency and version, grouped updates after the group | Open | Cause unknown. The docs say a dependency matching a group's `patterns` is combined into that group's PR, so this looks like either a uv-ecosystem limitation or a classification issue with four-part versions (inference). Next step: read the Dependabot job log for the #55 run (Insights → Dependency graph → Dependabot) before changing the config |
| Low | Merging #53 triggered an immediate Dependabot run (#54, #55 opened within a minute) | Resolved | Expected behaviour when the config changes (inference). Monthly cadence starts from here |
| Low | Network: the cloud session's environment initially allowed package registries only, so the GitHub docs and OSV were blocked. Advisory details first came from Stan via the Security tab | Resolved | Stan widened the environment's network access mid-session; docs and OSV were then read directly |
| Low | `qdrant-client` is a new transitive dependency via crewai | Open | Nothing known against it. Watch the Security tab |

## 4. Milestones
- [x] **No open Dependabot PRs; `main` green**
  - **Verification**: open-PR list empty after #54 merged; `make ci` on
    `a277604`: ruff, mypy strict, 28 tests passed (43 warnings, unchanged)
  - **Status**: Verified
- [x] **Version updates run monthly**
  - **Verification**: #53 merged; YAML parses; `quality` green
  - **Status**: Verified (Dependabot's own acceptance of the config is
    shown by it opening #54 / #55 against the new config)
- [x] **chromadb no longer installed**
  - **Verification**: no `chromadb` entry in `uv.lock`; `import chromadb`
    fails in the synced venv; crewai metadata lists it under
    `extra == 'chromadb'`
  - **Status**: Verified
- [ ] **chromadb alerts closed**
  - **Verification**: Security tab shows 0 open chromadb alerts
  - **Status**: Pending (depends on GitHub refreshing the dependency graph)

## 5. Learning Notes

### Commands / Code
- Command: `python -c "import importlib.metadata as m; print(m.requires('crewai'))"`
  - Purpose: read a package's declared requirements, including which are
    optional extras (`; extra == '…'`)
  - Key parameters: filter the list for the package you care about
  - Verification: compare with `uv tree --invert --package <name>`
  - Rollback: read-only
- Command: `git show <sha> -- uv.lock | grep '^-name\|^+name'`
  - Purpose: see which packages a lockfile change added or removed, not just
    the version bumps a PR title mentions
  - Key parameters: none
  - Verification: cross-check with `uv tree`
  - Rollback: read-only

### Concepts / Architecture
- Concept: Optional extras
  - One-line explanation: a dependency declared as `pkg; extra == 'x'` is
    installed only when someone asks for `parent[x]`.
  - Role in this project: crewai moving chromadb to an extra removed the
    project's entire chromadb attack surface without any change here. The
    Dependabot PR said "3 updates". The lockfile diff showed 17 packages
    removed. Read the lockfile diff, not the PR title.
- Concept: Hidden (undeclared) dependencies
  - One-line explanation: code that imports a package that happens to be
    installed transitively breaks when the transitive path disappears.
  - Role in this project: the X API spikes relied on `requests-oauthlib`
    arriving via chromadb → kubernetes. It was flagged on 2026-11-13 and broke
    today.
- Concept: Server-side vs library vulnerabilities
  - One-line explanation: an advisory against a package can target a component
    (here, Chroma's HTTP server) that a project using the package as a library
    never runs.
  - Role in this project: the reachability reasoning for the chromadb
    alerts rests on "no Chroma server". Severity alone (two criticals) would
    have overstated the risk.

## 6. Next Steps
- [ ] M4a PR 1: `guard.py`. X weighted length is implemented in-house (no
  third-party twitter-text port). Open a draft PR with the first commit
- [ ] M4a PR 2: choose and declare an OAuth 1.0a client library; move the
  spikes onto it
- [ ] Stan: confirm the four chromadb alerts closed in the Security tab
- [ ] Find out why the `type-stubs` group did not apply to #55
- [ ] ROADMAP check (needs Stan's approval): backlog items on chromadb,
  `type-stubs`, and Dependabot security updates are out of date; see Open
  Questions

## 7. Open Questions
- Why did the `type-stubs` group not catch `types-pyyaml`? The docs say it
  should have; the Dependabot job log is the next place to look.
- Is `qdrant-client` now loaded on import of crewai, and does CrewAI default to
  it when memory is enabled? Relevant only if memory is turned on (M5).
- Does `requests-oauthlib` belong in M4a PR 2 as the X client dependency, or
  is there a better-maintained option? Decide at PR 2 kickoff.

---

## 8. AI Handoff Snapshot

```
Project: crewai-factory
Date: 2026-11-26
Latest progress:
  - Current phase: M4a (publish path, verified on dev) — planned, no code yet
  - Completed today: Dependabot queue cleared (#51, #52, #54, #55);
    version updates moved to monthly + github-actions rule fixed (#53)
  - In progress: nothing. main at a277604, make ci green (28 tests)

Current architecture summary:
  - src/crewai_factory/: config, persona, agents, tasks, crew, flow, output
  - CrewAI Flow: strategist -> writer -> editor, retry until the editor passes
    (structured EditorVerdict), then save the draft to disk
  - No publish path yet: guard.py, x_client.py, ledger.py do not exist
  - crewai 1.15.44; chromadb is now an optional extra and NOT installed;
    qdrant-client is a new transitive dependency; ~135 locked packages

Next steps:
  - M4a PR 1: guard.py, pure functions, no LLM. X weighted length written
    in-house (CJK = 2, URL = 23); placeholder / meta-commentary check;
    near-duplicate check. Runs inside edit_draft before the editor crew; on
    violation synthesise EditorVerdict(score=0, ...). Open a draft PR early.
  - M4a PR 2 must declare an OAuth 1.0a library; the spikes currently fail
    on `import requests_oauthlib` (it left with chromadb)

For AI to be aware of:
  - Read docs/ROADMAP.md and the latest devlog before judging progress
  - Repo is public; ROADMAP and devlog writes need Stan's explicit approval
  - main is protected: PR only, required check `quality`, squash merges,
    branches must be up to date
  - Dependabot: version updates monthly; security updates arrive on their own
    and carry no `security` label (look for "automated security fix" in the
    body)
  - Verified against the docs: `schedule` governs version updates only;
    groups default to `applies-to: version-updates`
  - Unverified: why type-stubs grouping failed (#55), chromadb alerts
    auto-closing after the dependency graph refresh
```

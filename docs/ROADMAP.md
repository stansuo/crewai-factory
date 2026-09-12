# crewai-factory Roadmap

> **Version: v1.2** | **Last updated: 2026-09-12**
> Single source of truth for project milestones. Historical context lives in `docs/devlog/`.

---

## 1. TL;DR

- **Current milestone**: M4a — Publish path, verified on dev
- **Status**: M4 split into M4a / M4b (2026-09-12). M4a entry condition met (`main` green, dependencies current); work not yet started.
- **Completed**: M1 ✅ foundation fixes, M2 ✅ modular package + engineering foundation, X API spike ✅ (auth + read/write verified), pre-M3 hardening ✅, M3 ✅ CrewAI Flow (retry-until-pass)
- **Guiding principles**: security > maintainability > convenience; stabilize the text-only pipeline before adding features; GitHub Flow (feature branch → PR → main); public engine repo ships templates only — account-specific configuration lives in a private deployment repo

---

## 2. Milestones

### M1 ✅ Foundation fixes

**Completed**: 2026-04-28

Python downgraded 3.13 → 3.12 for dependency compatibility; base project structure established; core pipeline (strategist → writer → editor) running end-to-end.

---

### M2 ✅ Modular package + engineering foundation

**Completed**: 2026-06-04

**Deliverables**:
1. `src/crewai_factory/` — 8-module Python package (config, persona, agents, tasks, crew, output, `__init__`, `__main__`)
2. `personas/*.yaml` — YAML persona system with Pydantic schema validation; 3 demo personas (tech-blogger, cooking-creator, travel-storyteller)
3. Centralized env-var management with type validation via `pydantic-settings`
4. Structured logging with `loguru`
5. Collision-safe output filenames (timestamp + random token)
6. CLI (`--persona`, `--list-personas`, `--quiet`)
7. Test suite (pytest) + ruff + mypy strict + GitHub Actions CI
8. Makefile, MIT license, English README

---

### M3 ✅ Upgrade to CrewAI Flow

**Completed**: 2026-07-31

CrewAI Flow (`@start` / `@listen` / `@router`) replaced `Process.sequential`; writer retries until the editor passes it (configurable cap); editor verdict is structured (`EditorVerdict`, `output_pydantic`) and the router branches on typed fields; integration tests with mocked Ollama cover all Flow paths; `make demo` shows the retry count. Details in `docs/devlog/`.

---

### M4a 🔨 Publish path, verified on dev

**Goal**: A draft can only reach X after passing deterministic rules and an explicit human approval. `dry_run` is the default publish mode everywhere. Every publish attempt is recorded in a ledger that later milestones build on. Everything runs on the dev machine.

**Why split M4** (decided 2026-09-12): the original M4 bundled the X client and review gate (testable on dev) with deployment (credentials on a server for the first time). Splitting lets "first real post" and "first credentials on the server" happen as separate, individually reversible events.

**Not in scope**: hardening the editor verdict. With a human approval gate in front of every post, editor drift costs reading time but cannot publish a bad post; judge calibration is prompt iteration and belongs to M5a, which uses M4b's shadow-mode data.

**Entry condition**: ✅ `main` green, dependencies current (2026-09-12).

**Plan** — three PRs, each independently verifiable and revertable:

1. **Deterministic guard** — `guard.py`, pure functions, no LLM. Three rules: length within `persona.max_length` using X's weighted count (CJK = 2, URL = 23; `max_length` redefined as "X weighted units" and documented in the persona schema); no placeholders / meta-commentary; not a near-duplicate of recent published posts (from the ledger). Runs inside `edit_draft` before the editor crew is called; on violation it synthesises `EditorVerdict(score=0, feedback=<violations>)` so the existing router retries — no new flow topology. The same guard runs again immediately before any live publish.
2. **X client + `dry_run` default + SQLite ledger** — `Settings` gains `X_*` fields as `SecretStr` (closes the 2026-07-27 open item on unvalidated keys) and `publish_mode: "dry_run" | "live"` defaulting to `dry_run`. `x_client.py` posts via OAuth 1.0a user context (as in the spike). `ledger.py` uses stdlib `sqlite3`, one file, one table `posts` for now. SQLite over jsonl because the flow needs an update (fill in `tweet_id` after posting), M5b needs a second table joined on `tweet_id`, and two processes may write concurrently.
   - `posts` columns, **proposed, not yet reviewed — finalise at PR 2 kickoff**: `id, created_at, persona, topic, content_hash, content_path, editor_score, mode, approved_at, tweet_id, posted_at, http_status`. No M5 columns are pre-built.
3. **CLI approval and publish** — `python -m crewai_factory publish <draft.md>` reads a saved draft, re-runs the guard, posts, and updates the ledger row. Nothing publishes without this command. Publishing lives outside the Flow: `crew.run()` stays "generate and save", the Flow and its tests are untouched, and publishing is an explicit, separately triggerable step — the shape both the review gate and M4b's shadow mode need.

**Definition of done** (all required):
1. Guard merged with tests; a rule-violating draft cannot reach save or publish
2. `X_*` settings validated at startup; `publish_mode` defaults to `dry_run`
3. Ledger row written on every publish attempt in both modes, with `tweet_id` filled in on live success
4. One end-to-end live post from dev via the CLI approval path, using a demo persona and a non-sensitive test account with its own X developer app

**Optional spike** (any time, no dependency): `scripts/evals/judge_probe.py` — run the editor N=10 times on K=5 fixed drafts and record the score spread per draft in a devlog. ~50 cloud-model calls, no code change, not in CI.

---

### M4b 📋 Production deployment

**Goal**: Unattended runs on the always-on home server, shadow mode first, then live.

**Entry conditions**:
1. VPN link to the home server stable for several days (direct connection, not relayed)
2. Docker + Ollama container on the server can call a cloud model once
3. X API credentials re-verified (`scripts/spikes/test_x_api_get.py`)
4. Zero open items in private security notes
5. M4a DoD met

**Key decisions** (settled):
- Ollama deployed as separate infra, exposed over VPN only — never on the public internet
- Trigger mechanism: single-run container + systemd timer
- **Repo split** (2026-09-12): this public repo stays the generic engine and ships templates only (`docker-compose.prod.yml` skeleton, systemd `.service` / `.timer` examples). A separate private deployment repo holds real personas, the real compose override, the real timer schedule, and pins this repo by git tag or image tag. Secrets live only in the server's `.env`. Public devlogs, commits and README demos reference demo personas only. The ledger DB and all metrics data stay on the server.
- One X developer app per account; keys never shared across accounts
- Human review gate: CLI approval (M4a PR 3) is the baseline. A Telegram bot upgrade, if built, polls `getUpdates` (outbound only, no webhook) from the publisher run so it stays compatible with single-run + timer and no inbound exposure. A Web UI is not planned (requires an inbound service).

**Plan**:
- Prod compose: Ollama as its own service on an internal network; the app reaches it by service name; no host port for Ollama. Override file vs profiles decided here.
- systemd timer → `docker compose run --rm` single-run container
- loguru file sink with rotation + retention
- CrewAI telemetry / tracing: decide whether to disable; document how
- chromadb CVE-2026-45829 re-assessment (CrewAI memory still off → unreachable?)
- **Shadow mode**: deploy with `publish_mode=dry_run`, timer on, for at least one week; review drafts daily and record approve / reject in the ledger (this is M5a's calibration dataset). Only then flip to `live`. Separates "deployment broke" from "content is bad".

**Definition of done** (draft):
1. Timer fires on schedule for 7 days in `dry_run` with no failed runs
2. Logs readable on the server (file sink)
3. First live post from the server via the approval path

---

### M5 📋 Two feedback loops, then advanced features

Replaces the earlier single "performance tracking" line. The two loops answer different questions, use different data, and run on different time scales.

#### M5a — Inner loop: quality-gate calibration

- **Question**: does the editor's judgement agree with the human's?
- **Data**: shadow-mode ledger rows — `editor_score` vs human approve / reject
- **Work**: measure agreement rate; then, as evidence dictates: editor `temperature=0` (per-agent LLM), rubric booleans in `EditorVerdict` (`voice_ok`, `hook_ok`, `no_red_flags`) with gate = all booleans AND score ≥ threshold, majority-of-3 only if still noisy. Remove the stale free-text `Format: "Score: XX | …"` line from demo personas' editor backstory.
- **Exit**: agreement rate recorded before / after in a devlog

#### M5b — Outer loop: audience feedback, per-post time series

- **Question**: how does each post perform over time, and which topics / styles perform better?
- **Data model**: second table `metrics_snapshots(tweet_id, captured_at, hours_since_post, impressions, likes, replies, reposts, quotes, bookmarks)` — many rows per post
- **Collector**: its own single-run container + hourly systemd timer. Selects posts younger than 72 h (then daily until day 7), fetches `GET /2/tweets?ids=…&tweet.fields=public_metrics` (up to 100 ids per call → one call per hour regardless of post count), inserts one snapshot per post. The 1 / 6 / 12 / 24 / 48 / 72 h view is derived at analysis time from the nearest snapshot. Read-scope permission, `non_public_metrics` availability and read pricing to be verified against current X docs at M5b start.
- **Order**: collect and *see* first (pandas / small dashboard) → human adjusts persona or prompts with data → semi-automatic (e.g. top performers as writer few-shot examples) → fully automatic prompt rewriting last, and human-supervised. On a small account impressions are dominated by algorithm noise; reacting too early teaches engagement bait and drifts the persona.

#### M5c — Advanced features

Multi-model A/B → image generation → short video. Order unchanged: evaluation and feedback infrastructure first, commodity generation work later.

---

## 3. Backlog

- Remove migration dead code (`build_tasks`, sequential-`Crew` helpers, orphaned tests) as an isolated PR — ideally before M5a touches the verdict shape
- `dependabot.yml`: add a `types-*` pattern to the `minor-and-patch` group so type-stub bumps stop arriving as separate PRs
- Verify/enable Dependabot security updates
- Track chromadb CVE-2026-45829 (assessed unreachable — CrewAI memory not enabled); re-assess in M4b or if memory is turned on
- Adopt draft PRs on feature branches so CI runs on every push
- README demo section (GIF/asciinema + sample outputs) — record with demo personas only
- Persona strategy: single-language vs bilingual account track — now a private-deployment-repo concern; the public engine only needs `max_length` semantics (M4a PR 1)
- crewai deprecation warnings (`function_calling_llm`, `allow_code_execution`, `reasoning`) observed on 1.15.16 — not used by this project; review release notes carefully on the next crewai major bump

## 4. Decisions Log

| Date | Decision | Impact |
|---|---|---|
| 2026-04-28 | Python 3.13 → 3.12 | Full-stack version pin |
| 2026-04-28 | M3 uses CrewAI Flow, not Hierarchical Process | M3 architecture |
| 2026-04-28 | Trigger: single-run + systemd timer | M4 deployment |
| 2026-04-28 | Ollama as separate infra, VPN-only exposure | M4 deployment security |
| 2026-04-28 | GitHub Flow from M2 onward | Dev workflow |
| 2026-04-28 | Prompt iteration deferred to M5+ | Roadmap ordering |
| 2026-04-28 | Multi-model support: keep the seam, don't use it yet | M2 architecture |
| 2026-06-04 | Tests/CI scope merged into M2 | Milestone renumbering |
| 2026-06-04 | English README + MIT license | Portfolio visibility |
| 2026-07-07 | M5+ order: BI performance tracking before image generation | M5+ internal ordering |
| 2026-09-12 | M4 split into M4a (publish path on dev) and M4b (production deployment) | Milestone structure |
| 2026-09-12 | Public engine repo ships templates only; account-specific config in a private deployment repo | M4b architecture, security boundary |
| 2026-09-12 | Judge hardening moved from M4 to M5a; M5 split into inner loop (M5a) and outer loop (M5b, per-post time series) | Milestone structure, M5 ordering |
| 2026-09-12 | Ledger is SQLite (`posts` in M4a, `metrics_snapshots` in M5b) | Data model for M4–M5 |

---

## 5. Changelog

- **2026-07-15 (v1.0)**: Initial public roadmap, published with the repository.
- **2026-07-31 (v1.1)**: M3 complete — CrewAI Flow (retry-until-pass) merged (#19). Backlog updated (file-log sink → M4, dead-code removal).
- **2026-09-12 (v1.2)**: M4 split into M4a / M4b with entry conditions and DoD; M5 restructured into M5a (inner loop) / M5b (outer loop) / M5c; four decisions logged; Backlog refreshed after dependabot sweep (#24, #25).

---

*End of Roadmap v1.2*

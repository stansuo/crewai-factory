# crewai-factory Roadmap

> **Version: v1.0** | **Last updated: 2026-07-31**
> Single source of truth for project milestones. Historical context lives in `docs/devlog/`.

---

## 1. TL;DR

- **Current milestone**: M4 — X API integration + deployment
- **Status**: M3 complete (all five DoD items met, 2026-07-31). M4 not yet started; entry conditions to be confirmed.
- **Completed**: M1 ✅ foundation fixes, M2 ✅ modular package + engineering foundation, X API spike ✅ (auth + read/write verified), pre-M3 hardening ✅, M3 ✅ CrewAI Flow (retry-until-pass)
- **Guiding principles**: security > maintainability > convenience; stabilize the text-only pipeline before adding features; GitHub Flow (feature branch → PR → main)

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

**Goal**: Replace the sequential process with CrewAI Flow to enable retry-until-pass and richer control logic.

**Motivation**: In the current linear pipeline, when the editor rejects a draft, the run's final output is the rejection verdict itself — there is no loop back to the writer. Observed in real runs; this milestone closes that gap.

**Definition of done** (all required):
1. ✅`@start` / `@listen` / `@router` replace `Process.sequential`
2. ✅Writer automatically retries when the editor rejects (retry-until-pass, configurable cap)
3. ✅Editor verdict uses structured output (`output_pydantic`, typed `EditorVerdict`); the router branches on typed fields, never free-text parsing
4. ✅Integration tests (with mocked Ollama) cover the full Flow paths
5. ✅`make demo` shows observable retry behavior (verbose log includes retry count)

**Key decisions** (settled):
- CrewAI Flow (`@start` / `@listen` / `@router`) over Hierarchical Process — explicit, testable control flow
- retry-until-pass as default; best-of-N as an optional flag
- Structured editor verdict replaces prompt-format conventions

---

### M4 📋 X API integration + deployment

**Goal**: Automated posting via X API v2 + human review gate + production deployment on an always-on home server.

**De-risked in advance** (2026-07-05 spike):
- X API v2 read/write verified (`GET /2/users/me`, `POST /2/tweets`, OAuth 1.0a user context)
- Cost datapoint: ~0.02 USD / post (monthly cost model to be built during M4 scheduling design)
- Spike scripts kept under `scripts/spikes/` for reference; the production X client will be built with `pydantic-settings`-managed credentials

**Deployment context**:
- **Production**: always-on Linux home server; Ollama runs in Docker calling Ollama cloud models
- **Development**: WSL2 laptop
- Design implication: compose needs dev/prod separation (dev reaches host Ollama via host-gateway; prod reaches the Ollama container over an internal network). Mechanism (override file vs profiles) to be decided during M4 design.
- Cloud-model usage means the server holds outbound credentials → credential management is in M4 secrets scope (X API keys likewise)

**Key decisions** (settled):
- Ollama deployed as separate infra, exposed over VPN (Tailscale) only — never on the public internet
- Trigger mechanism: single-run container + systemd timer
- Human review gate: Telegram Bot vs Web UI, decided after M3 is validated

---

### M5+ 📋 Advanced features

**Goal**: Performance tracking + lightweight BI dashboard → prompt iteration → multi-model A/B → image generation.

**Order rationale**: performance tracking (pass rate, retry counts, per-persona/topic effectiveness) comes **before** image generation — it doubles as an evaluation story and plays to the project's data-analysis strengths, while image generation is commodity API work. Prompt iteration is deliberately deferred until the foundation is stable: tuning prompts on an unstable pipeline is guesswork.

---

## 3. Backlog

- home server: verify VPN connectivity stability (before M4)
- Compose dev/prod separation design (decide during M4); revisit Ollama port exposure surface at the same time
- Persona strategy: single-language vs bilingual account track (affects persona design and credential naming)
- README demo section (GIF/asciinema + sample outputs) — record **after** M3 (so the demo shows the retry loop, not a rejection verdict)
- Persistent file-log sink → M4: add a loguru file sink (rotation + retention) for post-hoc log inspection; location/rotation depend on the containerized deployment, so deferred until M4 design
- Remove migration dead code (`build_tasks`, sequential-`Crew` helpers, orphaned tests) as an isolated PR
- Verify/enable Dependabot security updates; revisit `dependabot.yml` grouping
- Track chromadb CVE-2026-45829 (assessed unreachable — CrewAI memory not enabled); re-assess at M4 or if memory is turned on
- Adopt draft PRs on feature branches so CI runs on every push

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

---

## 5. Changelog

- **2026-07-15 (v1.0)**: Initial public roadmap, published with the repository.

---

*End of Roadmap v1.0*

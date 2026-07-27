# crewai-factory

A CrewAI multi-agent pipeline that turns YAML personas into publish-ready
X (Twitter) posts, packaged with Docker. Long-term goal: a content factory that
runs unattended — text pipeline → performance tracking → self-optimisation →
image generation → short video.

**This repository is public.** Everything committed here — code, docs, commit
messages, PR and issue text — is world-readable. See `.claude/rules/security.md`,
which loads in every session.

## Start of session

Current milestone, progress, and priorities are deliberately not recorded in
this file. Read them:

1. `docs/ROADMAP.md` — single source of truth for milestones and backlog
2. the most recent files in `docs/devlog/` — what happened, and why
3. the repo itself for anything the docs don't answer

Do this before judging progress, editing code, or writing a devlog. Do not
assume the state of a branch from memory or from a previous session — branches
move between sessions.

Conceptual questions and planning discussion don't require it.

## Repository layout

| Repo | Visibility | Role |
|---|---|---|
| this repo | public | code, devlog, ROADMAP — also a job-search portfolio |
| private archive repo | private | pre-go-public history, `docs/private-notes/` |

The archive repo is deliberately not named in this file, because this file is
public. Its identity and how to reach it are in `CLAUDE.local.md`, which is
git-ignored. If that file isn't present, ask rather than guessing a name.

The public repo started with a fresh history. Devlog IDs predating it do not
resolve here — describe that history in prose rather than citing IDs.

## Commands

```
make ci          # lint + typecheck + test — run before every commit
make test        # pytest
make test-cov    # pytest with coverage
make lint        # ruff check + ruff format --check
make format      # ruff format + ruff check --fix
make typecheck   # mypy, strict
make run         # run the pipeline
make demo        # run with the tech-blogger persona
```

`make ci` mirrors the GitHub Actions `quality` job. The only difference is the
coverage flag, which does not affect pass/fail.

## Git workflow

GitHub Flow: feature branch → PR → main. `main` is ruleset-protected:

- no direct pushes
- required status check: `quality`
- branches must be up to date before merging
- squash merges only; head branches auto-delete

Two consequences worth holding in mind:

- Merging anything to `main` makes every other open PR stale. Batch merges
  need one update-branch-and-wait cycle per PR.
- Feature branches do not trigger CI — the workflow only runs on pushes to
  `main` and PRs targeting it. Open a draft PR early so lint and type errors
  surface the day they are written rather than weeks later.

## Devlog and ROADMAP

`docs/ROADMAP.md` is the single source of truth for milestones; `docs/devlog/`
is the append-only record of what happened and why. Conventions for both are in
`.claude/rules/devlog.md` and `.claude/rules/roadmap.md`, which load when
working under those paths. Read the relevant one — and
`docs/devlog/_DEVLOG_TEMPLATE.md` — before writing either.

The `整理 devlog`, `進行當日總結`, and `[CAUTION]` triggers are defined in
`~/.claude/CLAUDE.md` and apply here.

## Priorities

> Security > maintainability > convenience.
> Stabilise the text-only pipeline before adding features.

1. Never leak secrets or create a security risk; route content correctly
   between this repo and private notes
2. Never break a working state
3. End-to-end runnable and verifiable
4. Maintainable, iterable code
5. Advanced features — performance tracking, self-optimisation, image
   generation, video

Say so when an approach diverges from common industry practice, and offer the
safer or more standard alternative.

## Language

The engineering layer is English: code comments, docs, config comments,
devlogs, commit messages, PR and issue text. Deliberately multilingual content,
such as a zh-TW persona definition, is the exception. Conversation with Stan
is 繁體中文.

## Domain context

Stan is new to X automation and content automation. Offer high-level framing
when it helps — where a technique sits in the field, what the standard approach
is, why something is considered an anti-pattern.

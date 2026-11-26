---
paths:
  - ".github/**"
---

# GitHub Actions and repo automation

## Workflow permissions

Every workflow declares an explicit `permissions` block. Without one,
`GITHUB_TOKEN` inherits the repository default, which CodeQL flags as
`actions/missing-workflow-permissions` (CWE-275).

Default to the minimum at workflow level:

    permissions:
      contents: read

A job that needs write access opts in at the job level, not workflow-wide.

## Editing workflow files

`.github/workflows/` is protected: changing these files requires a token with
the `workflow` scope. An agent without it gets
`403 Resource not accessible by personal access token`.

That boundary is worth keeping. Do not suggest widening a token's scope to
avoid one manual edit — hand Stan the patch and let him commit it. The scope
exists so that a general-purpose token can't quietly rewrite CI.

`ci.yml` holds the required `quality` check. A malformed change there blocks
every merge in the repo, so it goes through a PR with green CI, never a direct
push.

## Dependabot

`.github/dependabot.yml` runs version updates monthly. It groups `types-*`
stubs into one PR, groups minor and patch updates into another, and leaves
major versions as individual PRs for review.

Dependabot opens two kinds of PR, and only one of them follows this file:

- **Version updates** follow `dependabot.yml`: its schedule and its groups.
- **Security updates** are triggered by alerts. They ignore the schedule,
  target the minimum patched version, can bump transitive dependencies, and
  arrive as individual PRs. Groups default to `applies-to: version-updates`,
  so the groups above do not batch them. No PR is opened for an alert without
  a patched version.

That distinction explains the observed behaviour that single-package
transitive PRs keep arriving despite the grouping: they are security updates.
Recognise one by the "automated security fix" note in the PR body; it carries
no `security` label. Schedule and `applies-to` behaviour checked against the
Dependabot options reference (2026-11-26); the PR-body marker is observed.

Known gap: the `type-stubs` group did not catch `types-pyyaml` in #55 even
though its pattern matches. Cause not yet found.

For handling the resulting PRs and judging their security impact, see
`.claude/rules/security.md`.

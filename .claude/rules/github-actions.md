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

`.github/dependabot.yml` groups minor and patch updates to reduce noise, and
leaves major versions as individual PRs for review.

Observed behaviour: transitive lockfile updates still arrive as individual PRs
regardless of the grouping. The likely cause is that grouping applies to direct
dependencies only — inferred from behaviour, not verified against the docs.

For handling the resulting PRs and judging their security impact, see
`.claude/rules/security.md`.

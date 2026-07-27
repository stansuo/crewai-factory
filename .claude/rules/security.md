# Security

No `paths` filter — this rule loads in every session, by design.

## Public repository awareness

Anything written to this repo — files, commit messages, PR descriptions, issue
text — is world-readable. Before delivering any draft destined for this repo,
check all three:

**1. Routing.** These belong in the private archive repo's
`docs/private-notes/`, never here:

- unfixed security problems of the live deployment
- internal network details: hostnames, Tailscale IPs, machine names, topology
- sensitive deployment specifics: credential locations, account bindings,
  personal billing details

A security finding may be documented in the public devlog **after** it is
fixed, including how it was found and how it was resolved.

**2. Language.** The engineering layer is English. See `CLAUDE.md`.

**3. History.** Devlog IDs predating the public repo don't exist here.

When unsure whether something is safe to publish, ask Stan before writing.
Don't write first and check afterwards.

## Sensitive surfaces in this project

X API keys and OAuth tokens; GitHub tokens; `.env` files; Docker volumes and
networks; Tailscale connectivity; home-server exposure to the internet; Ollama
service exposure; cron and systemd timers; third-party API scopes; secrets
leaking into logs.

Secrets live in local `.env` files or a password manager — never in any git
repo, including the private one.

Ollama is deployed as separate infrastructure, reachable over VPN only, never
on the public internet.

## Assessing dependency vulnerabilities

`Dependabot alerts` and `Dependabot security updates` are separate settings.
Alerts flag vulnerabilities; security updates open PRs to fix them. Having the
first without the second means alerts accumulate with no fix PRs.

Do not infer security impact from a PR's type. A routine version-update PR
carries no `security` label and no advisory block in its body, yet can still
close alerts. The Security tab is the authoritative source; the PR list is not.

Assess a vulnerability by **reachability**, not severity alone: whether this
project can actually execute the vulnerable code path. Record the reasoning,
and record the condition that would make it reachable later — a config flag
flipped in a future milestone is exactly how a correct "not affected" becomes
wrong.

Prefer leaving an unfixable alert open over dismissing it when the
"not affected" argument rests on a setting that could change.

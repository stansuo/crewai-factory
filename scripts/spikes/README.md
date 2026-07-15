# Spikes

One-off exploratory scripts ("spikes") used to de-risk external dependencies
before formal milestone work. These are **not** part of the `crewai_factory`
package, are **not** covered by CI (lint/typecheck/tests scan `src/` and
`tests/` only), and are kept for reference.

## Contents

| Script | Purpose | Date |
|---|---|---|
| `test_x_api_get.py` | Verify X API v2 auth via `GET /2/users/me` (OAuth 1.0a user context) | 2026-07-05 |
| `test_x_api_post.py` | Verify posting via `POST /2/tweets` (cost datapoint: ~0.02 USD/post) | 2026-07-05 |

The production X client will be built in **M4** using `pydantic-settings`.

## Running

Spikes are not part of the package and have one extra dependency:

    uv pip install requests-oauthlib

Then run from the project root, e.g. `uv run python scripts/spikes/test_x_api_get.py`.

Note: `uv sync` resets the venv to the lockfile, so re-install after each sync.

## Secret handling (non-negotiable)

- **Never hardcode keys** in these scripts, not even "temporarily".
- Keys live in the local `.env` (gitignored) only. The scripts load them
  via `python-dotenv` / environment variables (`X_*` names, see
  `.env.example`) and exit early if any are missing.

---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python conventions

Python 3.12, pinned `>=3.12,<3.13`. Dependencies managed by uv.

## Gates

`make ci` must pass before committing — ruff check, `ruff format --check`,
mypy strict, pytest.

- line length 88
- ruff rules: `E`, `F`, `I`, `N`, `UP`, `B`, `SIM`
- mypy strict over `src/`: every function annotated, and an empty body on a
  non-`None` return type is an error, not a placeholder

`ruff format` does not split string literals, so over-long f-strings have to be
wrapped by hand. It does wrap long conditional expressions.

## Package layout

`src/crewai_factory/` — `config`, `persona`, `agents`, `tasks`, `crew`,
`output`, `flow`.

Personas are YAML under `personas/`, validated by a Pydantic schema.

Configuration uses `pydantic-settings` in three layers: `config.py` holds the
schema and safe defaults, `.env.example` is the committed template, `.env`
holds real values and is git-ignored. Type validation catches a bad value at
startup rather than mid-run.

Logging is `loguru`.

## Typing against CrewAI

`Crew.kickoff()` is annotated as a union (`CrewOutput | CrewStreamingOutput`),
so reading an attribute that only one member has fails mypy strict. Narrow
before use — `isinstance`, or `getattr` followed by an `isinstance` check
against the expected model — rather than suppressing the error. Narrowing to
the concrete model also types the fields read from it afterwards.

A `Task` with `output_pydantic=Model` yields a typed object on
`result.pydantic`; free text stays on `result.raw`.

Technical failures fail fast and raise. They are not silently recovered.

## Flow conventions

Data passes through `self.state`. What triggers a `@listen` is the upstream
method finishing, not its return value — nodes return `None`. Only `@router`
returns a string, and that string is a routing label, not data.

Guard the container before the attribute: `if self.state.verdict` checks the
object exists; `if self.state.verdict.feedback` raises `AttributeError` on the
first cycle.

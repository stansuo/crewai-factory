"""Load and validate persona definitions from YAML files.

Each persona YAML drives the behaviour of the three-agent pipeline:
strategist → writer → editor.  This module turns that YAML into
validated, typed Python objects so the rest of the codebase never
touches raw dicts.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

# ── Schema ────────────────────────────────────────────────────────


class AgentProfile(BaseModel):
    """Prompt configuration for a single agent role."""

    goal: str
    backstory: str


class Voice(BaseModel):
    """Persona-level voice and identity settings."""

    tone: str
    perspective: str = "first-person"
    identity: str


class Persona(BaseModel):
    """Complete persona definition, mapping 1-to-1 with a YAML file."""

    name: str
    platform: str = "X (Twitter)"
    language: str = "en"
    max_length: int = 280

    voice: Voice
    strategist: AgentProfile
    writer: AgentProfile
    editor: AgentProfile


# ── Loader ────────────────────────────────────────────────────────


def load_persona(path: str | Path) -> Persona:
    """Read a persona YAML and return a validated Persona object.

    Raises:
        FileNotFoundError: YAML file does not exist.
        yaml.YAMLError: File is not valid YAML.
        pydantic.ValidationError: YAML content doesn't match schema.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    return Persona.model_validate(raw)


def list_personas(directory: str | Path = "personas") -> list[Path]:
    """Return all .yaml files in the personas directory, sorted by name."""
    d = Path(directory)
    if not d.is_dir():
        return []
    return sorted(d.glob("*.yaml"))

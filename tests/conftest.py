"""Shared fixtures for the test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from crewai_factory.config import Settings
from crewai_factory.persona import Persona

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_persona_path(tmp_path: Path) -> Path:
    """Write a minimal persona YAML to a temp file and return its path."""
    content = """\
name: "Test Bot"
platform: "X (Twitter)"
language: "en"
max_length: 280

voice:
  tone: "neutral"
  perspective: "first-person"
  identity: "A test persona for unit tests."

strategist:
  goal: "Generate a test topic."
  backstory: "You are a test strategist."

writer:
  goal: "Write a test post."
  backstory: "You are a test writer."

editor:
  goal: "Review the test post."
  backstory: "You are a test editor."
"""
    p = tmp_path / "test-persona.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def sample_persona(sample_persona_path: Path) -> Persona:
    """Return a loaded Persona from the sample YAML."""
    from crewai_factory.persona import load_persona

    return load_persona(sample_persona_path)


@pytest.fixture
def settings(sample_persona_path: Path, tmp_path: Path) -> Settings:
    """Return Settings pointed at temp dirs and the sample persona."""
    return Settings(
        persona_file=str(sample_persona_path),
        output_dir=tmp_path / "output",
        verbose=False,
    )

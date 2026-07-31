"""Assemble and execute the content-generation flow.

This is the top-level orchestrator.  It wires together:
  config → persona → flow → output

Callers (CLI, tests, future API) only need to call `run()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from crewai_factory.config import Settings
from crewai_factory.flow import ContentFlow
from crewai_factory.persona import Persona, load_persona


@dataclass
class RunResult:
    """Outcome of a single factory run."""

    content: str
    persona: Persona
    output_path: Path | None


def run(settings: Settings | None = None) -> RunResult:
    """Execute one full content-generation cycle.
    Returns a RunResult with the generated content and file path.
    """
    settings = settings or Settings()

    # ── Load persona ─────────────────────────────────────────────
    logger.info("Loading persona from {}", settings.persona_file)
    persona = load_persona(settings.persona_file)
    logger.info(
        "Persona '{}' loaded — platform={}, language={}",
        persona.name,
        persona.platform,
        persona.language,
    )

    # ── Build ContentFlow ───────────────────────────────────────────
    flow = ContentFlow(persona, settings)

    # ── Execute ──────────────────────────────────────────────────
    logger.info(
        "Running flow with model '{}' at {}",
        settings.ollama_model,
        settings.ollama_base_url,
    )

    flow.kickoff()

    saved_content = flow.state.saved_content
    output_path = flow.state.output_path

    if saved_content is None or output_path is None:
        raise RuntimeError("Content generation failed; no output saved.")

    logger.success("Post saved to {}", output_path)

    return RunResult(content=saved_content, persona=persona, output_path=output_path)

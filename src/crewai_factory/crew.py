"""Assemble and execute the content-generation crew.

This is the top-level orchestrator.  It wires together:
  config → persona → agents → tasks → crew → output

Callers (CLI, tests, future API) only need to call `run()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from crewai import Crew, Process
from loguru import logger

from crewai_factory.agents import build_agents
from crewai_factory.config import Settings
from crewai_factory.output import save_post
from crewai_factory.persona import Persona, load_persona
from crewai_factory.tasks import build_tasks


@dataclass
class RunResult:
    """Outcome of a single factory run."""

    content: str
    persona: Persona
    output_path: Path | None


def run(settings: Settings | None = None) -> RunResult:
    """Execute one full content-generation cycle.

    1. Load settings and persona
    2. Build agents and tasks
    3. Kick off the crew (sequential)
    4. Save output to disk

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

    # ── Build pipeline ───────────────────────────────────────────
    team = build_agents(persona, settings)
    tasks = build_tasks(team, persona)

    crew = Crew(
        agents=[team.strategist, team.writer, team.editor],
        tasks=tasks,
        process=Process.sequential,
        verbose=settings.verbose,
    )

    # ── Execute ──────────────────────────────────────────────────
    logger.info(
        "Running crew with model '{}' at {}",
        settings.ollama_model,
        settings.ollama_base_url,
    )
    result = crew.kickoff()
    content = result.raw if hasattr(result, "raw") else str(result)

    # ── Persist ──────────────────────────────────────────────────
    output_path = save_post(
        content, persona, settings.output_dir, model=settings.ollama_model
    )
    logger.success("Post saved to {}", output_path)

    return RunResult(content=content, persona=persona, output_path=output_path)

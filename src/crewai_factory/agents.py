"""Build CrewAI agents from a Persona definition.

Each persona maps to exactly three agents:
  1. Strategist — picks today's topic
  2. Writer     — drafts the post
  3. Editor     — quality-gates the output

This module owns agent *construction*, not execution.
Execution lives in crew.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from crewai import LLM, Agent

from crewai_factory.config import Settings
from crewai_factory.persona import Persona


@dataclass(frozen=True)
class AgentTeam:
    """The three agents that form a content-creation crew."""

    strategist: Agent
    writer: Agent
    editor: Agent


def build_llm(settings: Settings) -> LLM:
    """Construct the shared LLM backend from settings."""
    return LLM(
        model=f"ollama/{settings.ollama_model}",
        base_url=settings.ollama_base_url,
        temperature=settings.temperature,
    )


def build_agents(persona: Persona, settings: Settings) -> AgentTeam:
    """Create the three-agent team from a persona and settings."""
    llm = build_llm(settings)
    common = dict(
        llm=llm,
        verbose=settings.verbose,
        max_iter=settings.max_agent_iterations,
    )

    strategist = Agent(
        role="Content strategist",
        goal=persona.strategist.goal,
        backstory=persona.strategist.backstory,
        **common,
    )

    writer = Agent(
        role=f"{persona.platform} post writer",
        goal=persona.writer.goal,
        backstory=persona.writer.backstory,
        **common,
    )

    editor = Agent(
        role="Quality editor",
        goal=persona.editor.goal,
        backstory=persona.editor.backstory,
        **common,
    )

    return AgentTeam(strategist=strategist, writer=writer, editor=editor)

"""crewai-factory — A configurable multi-agent content generation framework.

Orchestrates three AI agents (strategist → writer → editor) to produce
publish-ready social media posts, driven entirely by YAML persona files.
"""

from crewai_factory.config import Settings
from crewai_factory.crew import RunResult, run
from crewai_factory.persona import Persona, load_persona

__all__ = ["Settings", "Persona", "RunResult", "load_persona", "run"]

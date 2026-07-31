"""Application configuration via environment variables.

Uses pydantic-settings so every value is validated at startup.
Override any field with an environment variable of the same name
(case-insensitive) or by placing it in a .env file.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — single source of truth for all runtime params."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # silently drop unknown env vars
    )

    # ── LLM backend ──────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:120b-cloud"
    temperature: float = 0.7

    # ── Persona ──────────────────────────────────────────────────
    persona_file: str = "personas/tech-blogger.yaml"

    # ── Output ───────────────────────────────────────────────────
    output_dir: Path = Path("output")

    # ── Execution ────────────────────────────────────────────────
    max_agent_iterations: int = 3
    quality_threshold: int = 85  # editor pass bar; gate is score >= this
    verbose: bool = True

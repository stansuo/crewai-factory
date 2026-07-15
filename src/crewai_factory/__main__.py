"""CLI entrypoint — run with `python -m crewai_factory` or `run-factory`.

Examples:
    python -m crewai_factory
    python -m crewai_factory --persona personas/cooking-creator.yaml
    python -m crewai_factory --list-personas
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from loguru import logger

from crewai_factory.config import Settings
from crewai_factory.crew import run
from crewai_factory.persona import list_personas


def _configure_logging(verbose: bool) -> None:
    """Set up loguru with a sensible default format."""
    logger.remove()  # drop the default stderr handler
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> — "
            "<level>{message}</level>"
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crewai-factory",
        description="Multi-agent content generation framework",
    )
    parser.add_argument(
        "--persona",
        type=str,
        default=None,
        help="Path to a persona YAML file (overrides PERSONA_FILE env var)",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available persona files and exit",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce log output to warnings and errors",
    )
    args = parser.parse_args()

    # ── List mode ────────────────────────────────────────────────
    if args.list_personas:
        personas = list_personas()
        if not personas:
            print("No persona files found in personas/")
            sys.exit(1)
        print("Available personas:")
        for p in personas:
            print(f"  {p}")
        sys.exit(0)

    # ── Run mode ─────────────────────────────────────────────────
    overrides: dict[str, Any] = {}
    if args.persona:
        overrides["persona_file"] = args.persona
    settings = Settings(**overrides)

    _configure_logging(verbose=not args.quiet and settings.verbose)

    logger.info("Starting crewai-factory")
    try:
        result = run(settings)
    except FileNotFoundError as exc:
        logger.error("{}", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Factory run failed")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(result.content)
    print("=" * 60)
    print(f"\nSaved to: {result.output_path}")


if __name__ == "__main__":
    main()

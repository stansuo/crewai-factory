"""Persist generated posts to the output directory.

Filenames include a timestamp with seconds plus a random token,
so concurrent or rapid successive runs can never collide.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path

from crewai_factory.persona import Persona


def _safe_filename(persona_name: str, now: datetime, failed: bool) -> str:
    """Build a collision-resistant filename from persona name + timestamp.

    A random 6-char hex token (secrets.token_hex) supplies real entropy;
    hashing the timestamp would be deterministic and could not prevent
    collisions for runs within the same second.
    """
    slug = persona_name.lower().replace(" ", "-")[:20]
    ts = now.strftime("%Y%m%d_%H%M%S")
    token = secrets.token_hex(3)  # 6-character hex string
    filename = f"post_{slug}_{ts}_{token}{'_failed' if failed else ''}.md"
    return filename


def save_post(
    content: str,
    persona: Persona,
    output_dir: Path,
    model: str = "unknown",
    *,
    now: datetime | None = None,
    failed: bool = False,
) -> tuple[Path, str]:
    """Write a generated post to a markdown file and return its path and content.

    The output directory is created if it doesn't exist.
    """
    now = now or datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_filename(persona.name, now, failed)
    filepath = output_dir / filename

    header = (
        f"{'**Status**: FAILED\n\n' if failed else ''}"
        f"# {persona.name} — AI-generated {persona.platform} post\n\n"
        f"**Date**: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**Persona**: {persona.name}\n"
        f"**Language**: {persona.language}\n"
        f"**Model**: {model}\n\n"
        f"---\n\n"
    )

    filepath.write_text(header + content, encoding="utf-8")
    return (filepath, content)

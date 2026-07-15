"""Define the task pipeline for content generation.

The pipeline is always: strategise → write → edit.
Tasks are parameterised by the persona (language, max_length, voice)
so the same code works for any persona YAML.
"""

from __future__ import annotations

from datetime import datetime

from crewai import Task

from crewai_factory.agents import AgentTeam
from crewai_factory.persona import Persona


def build_tasks(team: AgentTeam, persona: Persona) -> list[Task]:
    """Return the ordered task list for a sequential crew run."""
    today = datetime.now().strftime("%Y-%m-%d")

    task_strategise = Task(
        description=(
            f"Today is {today}. "
            f"Based on the persona '{persona.name}' and its voice identity, "
            f"generate exactly one compelling topic for a {persona.platform} post "
            f"in {persona.language}."
        ),
        expected_output=(
            "A single topic sentence (under 50 words). No additional explanation."
        ),
        agent=team.strategist,
    )

    task_write = Task(
        description=(
            f"Using the topic from the strategist, write a complete "
            f"{persona.platform} post in {persona.language}.\n"
            f"Voice: {persona.voice.tone}\n"
            f"Perspective: {persona.voice.perspective}\n"
            f"Maximum length: {persona.max_length} characters.\n"
            f"The post must be ready to publish — no placeholders, "
            f"no meta-commentary."
        ),
        expected_output=(
            f"A complete, publish-ready {persona.platform} post. Nothing else."
        ),
        agent=team.writer,
    )

    task_edit = Task(
        description=(
            "Review the writer's post against these criteria:\n"
            "1. Voice consistency with the persona\n"
            "2. Engagement potential (would someone reply or share?)\n"
            f"3. Length within {persona.max_length} characters\n"
            "4. No factual red flags or policy violations\n\n"
            "Score from 0-100. Only approve posts scoring 85+."
        ),
        expected_output=(
            "Score: XX | Verdict: PASS/FAIL | Feedback: ...\n"
            "If PASS, include the final post text below the verdict."
        ),
        agent=team.editor,
    )

    return [task_strategise, task_write, task_edit]

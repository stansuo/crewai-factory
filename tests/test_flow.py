from unittest.mock import Mock

import pytest
from crewai import Crew, CrewOutput
from crewai.settings import Settings

from crewai_factory.flow import ContentFlow
from crewai_factory.persona import Persona
from crewai_factory.tasks import EditorVerdict


def fake_output(
    score: int | None = None,
    raw: str = "",
    feedback: str = "test feedback",
) -> CrewOutput:

    if score is None:
        return CrewOutput(raw=raw)

    verdict = EditorVerdict(score=score, feedback=feedback)
    return CrewOutput(raw=raw, pydantic=verdict)


class TestContentFlow:
    def test_flow_pass_first(
        self,
        sample_persona: Persona,
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        side_effect = [
            fake_output(raw="a topic"),  # generate_topic 拿到的
            fake_output(raw="draft01"),  # write_draft 第1次
            fake_output(score=90),  # edit_draft 第1次 → 過，save
        ]
        monkeypatch.setattr(Crew, "kickoff", Mock(side_effect=side_effect))

        content_flow = ContentFlow(sample_persona, settings)
        content_flow.kickoff()

        assert content_flow.state.topic == "a topic"
        assert content_flow.state.verdict is not None
        assert content_flow.state.verdict.score == 90
        assert len(content_flow.state.attempts) == 1
        assert content_flow.state.saved_content == "draft01"

    def test_flow_retry_then_pass(
        self,
        sample_persona: Persona,
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        side_effect = [
            fake_output(raw="a topic"),  # generate_topic 拿到的
            fake_output(raw="draft01"),  # write_draft 第1次
            fake_output(score=70),  # edit_draft 第1次 → 不過，retry
            fake_output(raw="draft02"),  # write_draft 第2次
            fake_output(score=90),  # edit_draft 第2次 → 過，save
        ]
        monkeypatch.setattr(Crew, "kickoff", Mock(side_effect=side_effect))

        content_flow = ContentFlow(sample_persona, settings)
        content_flow.kickoff()

        assert content_flow.state.topic == "a topic"
        assert content_flow.state.verdict is not None
        assert content_flow.state.verdict.score == 90
        assert len(content_flow.state.attempts) == 2
        assert content_flow.state.saved_content == "draft02"

    def test_flow_cap_exhaustion(
        self,
        sample_persona: Persona,
        settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        side_effect = [
            fake_output(raw="a topic"),  # generate_topic 拿到的
            fake_output(raw="draft01"),  # write_draft 第1次
            fake_output(score=80),  # edit_draft 第1次 → 不過，retry
            fake_output(raw="draft02"),  # write_draft 第2次
            fake_output(score=75),  # edit_draft 第2次 → 不過，retry
            fake_output(raw="draft03"),  # write_draft 第3次
            fake_output(score=70),  # edit_draft 第3次 → 不過，handle_failure
        ]
        monkeypatch.setattr(Crew, "kickoff", Mock(side_effect=side_effect))

        content_flow = ContentFlow(sample_persona, settings)
        content_flow.kickoff()

        assert content_flow.state.topic == "a topic"
        assert content_flow.state.verdict is not None
        assert content_flow.state.verdict.score == 70
        assert len(content_flow.state.attempts) == 3
        assert content_flow.state.saved_content == "draft01"

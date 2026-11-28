import runpy
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from crewai import Crew, CrewOutput

from crewai_factory.config import Settings
from crewai_factory.crew import run
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


def test_cli_retries_until_corrected(
    tmp_path: Path,
    sample_persona_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("QUALITY_THRESHOLD", "0")
    monkeypatch.setattr(
        sys, "argv", ["run-factory", "--persona", str(sample_persona_path)]
    )
    kickoff = Mock(
        side_effect=[
            fake_output(raw="a topic"),
            fake_output(raw="TODO"),
            fake_output(raw="Done."),
            fake_output(score=0),
        ]
    )
    monkeypatch.setattr(Crew, "kickoff", kickoff)
    runpy.run_module("crewai_factory", run_name="__main__")
    assert kickoff.call_count == 4
    assert "Done." in capsys.readouterr().out
    (path,) = (tmp_path / "posts").glob("*.md")
    assert path.read_text().endswith("Done.")


@pytest.mark.parametrize(
    "draft",
    [
        "界" * 141,
        "\ufeff",
        "a" * 255 + " #" + "b" * 50 + ".com",
        "a" * 256 + " example.com?x=1",
        "🇦🇦" * 71,
        "a" * 256 + " https://t.co/a/long/path",
        "a" * 271 + " café.com",
    ],
)
def test_cli_exhausted_guard_saves_nothing(
    draft: str,
    tmp_path: Path,
    sample_persona_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "posts"))
    monkeypatch.setattr(
        sys, "argv", ["run-factory", "--persona", str(sample_persona_path)]
    )
    monkeypatch.setenv("QUALITY_THRESHOLD", "0")
    kickoff = Mock(
        side_effect=[fake_output(raw="topic")] + [fake_output(raw=draft)] * 3
    )

    def respond(crew: Crew) -> CrewOutput:
        assert crew.tasks[0].output_pydantic is None, "Rejected draft reached editor"
        return kickoff()

    monkeypatch.setattr(Crew, "kickoff", respond)
    with pytest.raises(SystemExit) as error:
        runpy.run_module("crewai_factory", run_name="__main__")
    assert error.value.code == 1
    assert kickoff.call_count == 4
    assert not (tmp_path / "posts").exists()


def test_failed_fallback_skips_duplicate_even_on_tied_score(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = "Time to brew a fresh cup of coffee."
    valid = "Which tea do you drink in summer?"
    kickoff = Mock(
        side_effect=[
            fake_output(raw="a topic"),
            fake_output(raw=previous.upper()),
            fake_output(raw=valid),
            fake_output(score=0),
            fake_output(raw="Final answer: x"),
        ]
    )
    monkeypatch.setattr(Crew, "kickoff", kickoff)
    result = run(settings, recent_posts=[previous])
    assert kickoff.call_count == 5
    assert result.content == valid
    assert result.output_path is not None
    assert result.output_path.name.endswith("_failed.md")

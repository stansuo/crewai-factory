"""Tests for crewai_factory.output."""

from datetime import datetime
from pathlib import Path

from crewai_factory.output import save_post
from crewai_factory.persona import Persona


class TestSavePost:
    def test_creates_file(self, sample_persona: Persona, tmp_path: Path) -> None:
        path, _ = save_post("Hello world", sample_persona, tmp_path)
        assert path.exists()
        assert path.suffix == ".md"

    def test_file_contains_content(
        self, sample_persona: Persona, tmp_path: Path
    ) -> None:
        path, returned_content = save_post(
            "Test content here", sample_persona, tmp_path
        )
        text = path.read_text(encoding="utf-8")
        assert "Test content here" in text
        assert returned_content == "Test content here"

    def test_file_contains_header(
        self, sample_persona: Persona, tmp_path: Path
    ) -> None:
        path, _ = save_post("Content", sample_persona, tmp_path)
        text = path.read_text(encoding="utf-8")
        assert "Test Bot" in text
        assert "AI-generated" in text

    def test_header_contains_model(
        self, sample_persona: Persona, tmp_path: Path
    ) -> None:
        path, _ = save_post("Content", sample_persona, tmp_path, model="test-model:1b")
        text = path.read_text(encoding="utf-8")
        assert "**Model**: test-model:1b" in text

    def test_filename_includes_persona_slug(
        self, sample_persona: Persona, tmp_path: Path
    ) -> None:
        path, _ = save_post("Content", sample_persona, tmp_path)
        assert "test-bot" in path.name

    def test_creates_output_dir(self, sample_persona: Persona, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested" / "dir"
        path, _ = save_post("Content", sample_persona, nested)
        assert path.exists()
        assert nested.is_dir()

    def test_same_time_no_collision(
        self, sample_persona: Persona, tmp_path: Path
    ) -> None:
        # Two runs within the same second must NOT overwrite each other.
        fixed = datetime(2026, 6, 4, 12, 0, 0)
        p1, _ = save_post("A", sample_persona, tmp_path, now=fixed)
        p2, _ = save_post("B", sample_persona, tmp_path, now=fixed)
        assert p1.name != p2.name
        assert p1.read_text(encoding="utf-8").endswith("A")
        assert p2.read_text(encoding="utf-8").endswith("B")

    def test_different_times_different_files(
        self, sample_persona: Persona, tmp_path: Path
    ) -> None:
        t1 = datetime(2026, 6, 4, 12, 0, 0)
        t2 = datetime(2026, 6, 4, 12, 0, 1)
        p1, _ = save_post("A", sample_persona, tmp_path, now=t1)
        p2, _ = save_post("B", sample_persona, tmp_path, now=t2)
        assert p1.name != p2.name

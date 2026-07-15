"""Tests for crewai_factory.persona."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from crewai_factory.persona import Persona, list_personas, load_persona


class TestLoadPersona:
    def test_loads_valid_yaml(self, sample_persona_path: Path) -> None:
        persona = load_persona(sample_persona_path)
        assert isinstance(persona, Persona)
        assert persona.name == "Test Bot"

    def test_fields_populated(self, sample_persona: Persona) -> None:
        assert sample_persona.platform == "X (Twitter)"
        assert sample_persona.language == "en"
        assert sample_persona.max_length == 280

    def test_voice_loaded(self, sample_persona: Persona) -> None:
        assert sample_persona.voice.tone == "neutral"
        assert sample_persona.voice.perspective == "first-person"

    def test_agent_profiles_loaded(self, sample_persona: Persona) -> None:
        assert "test topic" in sample_persona.strategist.goal.lower()
        assert "test post" in sample_persona.writer.goal.lower()
        assert "review" in sample_persona.editor.goal.lower()


class TestLoadPersonaErrors:
    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_persona("nonexistent/path.yaml")

    def test_invalid_schema_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("name: missing-everything\n", encoding="utf-8")
        with pytest.raises(ValidationError):  # pydantic ValidationError
            load_persona(bad)

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("", encoding="utf-8")
        with pytest.raises((ValidationError, AttributeError)):
            load_persona(empty)


class TestListPersonas:
    def test_lists_yaml_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").touch()
        (tmp_path / "b.yaml").touch()
        (tmp_path / "not-yaml.txt").touch()
        result = list_personas(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".yaml" for p in result)

    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        (tmp_path / "zebra.yaml").touch()
        (tmp_path / "alpha.yaml").touch()
        result = list_personas(tmp_path)
        assert result[0].name == "alpha.yaml"

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert list_personas(tmp_path) == []

    def test_nonexistent_dir(self) -> None:
        assert list_personas("/no/such/dir") == []

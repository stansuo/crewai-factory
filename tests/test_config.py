"""Tests for crewai_factory.config."""

from pathlib import Path

from crewai_factory.config import Settings


class TestSettingsDefaults:
    def test_default_ollama_url(self) -> None:
        s = Settings()
        assert s.ollama_base_url == "http://localhost:11434"

    def test_default_model(self) -> None:
        s = Settings()
        assert s.ollama_model == "gpt-oss:120b-cloud"

    def test_default_temperature(self) -> None:
        s = Settings()
        assert s.temperature == 0.7

    def test_output_dir_is_path(self) -> None:
        s = Settings()
        assert isinstance(s.output_dir, Path)


class TestSettingsOverride:
    def test_override_via_constructor(self) -> None:
        s = Settings(ollama_model="gemma3:4b", temperature=0.5)
        assert s.ollama_model == "gemma3:4b"
        assert s.temperature == 0.5

    def test_override_via_env(self, monkeypatch: object) -> None:

        monkeypatch.setenv("OLLAMA_MODEL", "phi4:latest")  # type: ignore[attr-defined]
        s = Settings()
        assert s.ollama_model == "phi4:latest"

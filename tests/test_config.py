"""Tests for application settings."""

from src.embeddings_api.config import Settings


class TestDocsEnabledSetting:
    """Tests for the docs_enabled configuration field."""

    def test_docs_enabled_defaults_to_true(self):
        """Without DOCS_ENABLED env var, docs should be enabled by default."""
        settings = Settings()
        assert settings.docs_enabled is True

    def test_docs_enabled_false_from_env(self, monkeypatch):
        """DOCS_ENABLED=false should disable docs."""
        monkeypatch.setenv("DOCS_ENABLED", "false")
        settings = Settings()
        assert settings.docs_enabled is False

    def test_docs_enabled_true_from_env(self, monkeypatch):
        """DOCS_ENABLED=true should enable docs."""
        monkeypatch.setenv("DOCS_ENABLED", "true")
        settings = Settings()
        assert settings.docs_enabled is True

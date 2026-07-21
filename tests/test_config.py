"""Tests for config.Settings and require_database_url (no DB needed)."""

import pytest

from research_agent.config import Settings, get_settings, require_database_url
from research_agent.errors import ConfigError


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch):
    """Keep config tests hermetic: never read the real .env."""
    monkeypatch.setattr("research_agent.config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr("research_agent.config._dotenv_loaded", False)


def test_get_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://host:5432/db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.database_url == "postgresql://host:5432/db"
    assert settings.anthropic_api_key == "sk-ant-test"
    assert settings.tavily_api_key == "tvly-test"


def test_get_settings_missing_keys_are_none(monkeypatch):
    for var in ("DATABASE_URL", "ANTHROPIC_API_KEY", "TAVILY_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    settings = get_settings()
    assert settings.database_url is None
    assert settings.anthropic_api_key is None
    assert settings.tavily_api_key is None


def test_require_database_url_returns_when_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://host:5432/db")
    assert require_database_url() == "postgresql://host:5432/db"


def test_require_database_url_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigError):
        require_database_url()

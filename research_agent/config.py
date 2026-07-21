"""Application configuration — single source of truth for environment settings.

Reads the environment once (loading a ``.env`` file if present) so the CLI, MCP
server, web service, and worker share one config seam instead of scattered
``os.environ`` lookups.  ``DATABASE_URL`` is required for anything that touches
Postgres; the API keys stay optional here (they are validated at their point of
use, as they were before this module existed).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import ConfigError

_dotenv_loaded = False


def _ensure_dotenv() -> None:
    """Load ``.env`` once per process (idempotent)."""
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv()
        _dotenv_loaded = True


@dataclass(frozen=True)
class Settings:
    """Environment-derived settings, read via :func:`get_settings`."""

    database_url: str | None
    anthropic_api_key: str | None
    tavily_api_key: str | None


def get_settings() -> Settings:
    """Return the current environment settings (loads ``.env`` on first call)."""
    _ensure_dotenv()
    return Settings(
        database_url=os.environ.get("DATABASE_URL"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        tavily_api_key=os.environ.get("TAVILY_API_KEY"),
    )


def require_database_url() -> str:
    """Return ``DATABASE_URL`` or fail fast with an actionable message.

    Point it at the Supabase **session pooler** (port 5432) — see the Phase A
    plan for why session mode (not the 6543 transaction pooler) is used here.
    """
    url = get_settings().database_url
    if not url:
        raise ConfigError(
            "DATABASE_URL is not set. Point it at the Supabase session pooler "
            "(port 5432), e.g. "
            "postgresql://postgres.<ref>:<pw>@aws-<region>.pooler.supabase.com:5432/postgres"
        )
    return url

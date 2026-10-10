"""Load and validate non-secret Phase 0 settings from the process environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Validated application settings; construction does not create directories."""

    environment: str
    log_level: str


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Use process variables by default, or an explicit mapping for offline tests.

    Missing values have defaults. Empty or unsupported values are rejected.
    This function intentionally does not search for or load a .env file.
    """
    values = os.environ if environ is None else environ
    environment = values.get("AGENT_DEMO_ENV", "development").strip().lower()
    log_level = values.get("AGENT_DEMO_LOG_LEVEL", "INFO").strip().upper()
    if environment not in {"development", "test", "production"}:
        raise ValueError("AGENT_DEMO_ENV must be development, test, or production")
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ValueError("AGENT_DEMO_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    return Settings(environment=environment, log_level=log_level)


@dataclass(frozen=True)
class ModelSettings:
    """Explicit Gemini configuration; credentials are excluded from repr."""

    api_key: str = field(repr=False)
    model: str = "gemini-3.5-flash-lite"


def load_model_settings(environ: Mapping[str, str] | None = None) -> ModelSettings:
    """Read only process configuration, never search the old RAG project for keys."""
    values = os.environ if environ is None else environ
    key = values.get("GEMINI_API_KEY") or values.get("GOOGLE_API_KEY") or ""
    model = values.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    if not key.strip():
        raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY in the process environment")
    if not model or len(model) > 100 or any(char.isspace() for char in model):
        raise ValueError("GEMINI_MODEL must be a nonempty model identifier")
    return ModelSettings(api_key=key.strip(), model=model)

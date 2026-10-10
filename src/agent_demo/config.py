"""Load and validate non-secret Phase 0 settings from the process environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


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

"""Validate configuration and the installed package, independently of the repo cwd."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import agent_demo
from agent_demo.config import load_settings


def test_explicit_mapping_is_independent_of_process_environment(monkeypatch):
    monkeypatch.setenv("AGENT_DEMO_ENV", "production")
    monkeypatch.setenv("AGENT_DEMO_LOG_LEVEL", "ERROR")
    defaults = load_settings({})
    assert defaults.environment == "development"
    assert defaults.log_level == "INFO"
    assert load_settings().environment == "production"
    assert load_settings().log_level == "ERROR"


def test_environment_values_are_normalized():
    settings = load_settings({"AGENT_DEMO_ENV": " Test ", "AGENT_DEMO_LOG_LEVEL": " debug "})
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize(
    ("name", "value"),
    [("AGENT_DEMO_ENV", ""), ("AGENT_DEMO_ENV", "staging"), ("AGENT_DEMO_LOG_LEVEL", "verbose")],
)
def test_invalid_configuration_fails_early(name, value):
    with pytest.raises(ValueError, match=name):
        load_settings({name: value})


def test_editable_install_imports_from_source_outside_repo(tmp_path):
    # -I ignores PYTHONPATH and excludes the working directory from import lookup.
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import json, agent_demo; from importlib.metadata import version; "
            "print(json.dumps({'file': agent_demo.__file__, 'version': version('agent-demo')}))",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    installed = json.loads(result.stdout)
    expected = Path(__file__).resolve().parents[1] / "src" / "agent_demo" / "__init__.py"
    assert Path(installed["file"]).resolve() == expected
    assert Path(agent_demo.__file__).resolve() == expected
    assert installed["version"]

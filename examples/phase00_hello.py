"""Inspect the installed package and environment without calling an LLM."""

import json
import platform
import sys
from importlib.metadata import version

import agent_demo
from agent_demo.config import load_settings


def main() -> None:
    settings = load_settings()
    print(
        json.dumps(
            {
                "package": "agent-demo",
                "package_version": version("agent-demo"),
                "package_file": agent_demo.__file__,
                "python": platform.python_version(),
                "executable": sys.executable,
                "virtual_environment": sys.prefix != sys.base_prefix,
                "platform": platform.platform(),
                "environment": settings.environment,
                "log_level": settings.log_level,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

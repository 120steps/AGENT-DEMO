"""Run five deterministic MOCK scenarios without credentials."""

import json

from agent_demo.domain.mock_cases import scenarios
from agent_demo.graphs.compliance_graph import run_workflow


def main():
    for name, (requirements, evidences) in scenarios().items():
        result = run_workflow(requirements, evidences=evidences)
        # JSON escapes keep Chinese source text lossless on legacy Windows consoles.
        print(json.dumps({"scenario": name, **result.model_dump()}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

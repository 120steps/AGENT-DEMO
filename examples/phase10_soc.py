"""Local SOC CLI: submit/run/status/review/export, or locate PDF clauses."""

import argparse
import json
from pathlib import Path

from agent_demo.soc.rfp import parse_rfp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--owner", default="local-operator")
    parser.add_argument(
        "command", choices=["submit", "run", "status", "review", "export", "parse-pdf"]
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "parse-pdf":
            result = parse_rfp(args.input.read_bytes()).model_dump(mode="json")
        else:
            from agent_demo.soc.service import service_from_environment

            service = service_from_environment(args.root)
            if args.command == "submit":
                result = {
                    "task_id": service.submit(
                        json.loads(args.input.read_text("utf-8-sig")), args.owner
                    )
                }
            elif args.command == "run":
                result = service.run(args.task_id, args.owner)
            elif args.command == "status":
                result = service.status(args.task_id, args.owner)
            elif args.command == "review":
                result = service.review(
                    args.task_id, args.owner, json.loads(args.input.read_text("utf-8-sig"))
                )
            else:
                result = service.export(args.task_id, args.owner, draft=args.draft)
        print(json.dumps(result, ensure_ascii=True))
        return 1 if result.get("status") == "failed" else 0
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

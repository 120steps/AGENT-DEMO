"""Local evaluation, replay, and payload-free trace lookup. Never auto-start RAG."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from agent_demo.evaluation.runner import run_evaluation
from agent_demo.observability import read_trace


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=root / "eval/agent_test_cases.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case", action="append", help="Replay an explicit case ID (repeatable)")
    parser.add_argument("--include-live", action="store_true")
    parser.add_argument("--no-benchmarks", action="store_true")
    parser.add_argument("--save-baseline", action="store_true")
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.trace:
            if not args.run_id:
                parser.error("--trace requires --run-id")
            print(json.dumps(read_trace(args.trace, args.run_id), ensure_ascii=True))
            return 0
        directory = args.output or root / "outputs/phase08" / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        )
        report = run_evaluation(
            args.dataset,
            directory,
            selected=args.case,
            include_live=args.include_live,
            benchmarks=not args.no_benchmarks,
            save_baseline=root / "eval/reports" if args.save_baseline else None,
        )
        print(
            json.dumps(
                {"report_directory": str(directory), "metrics": report["metrics"]},
                ensure_ascii=True,
            )
        )
        return 0 if report["metrics"]["hard_gate_passed"] else 1
    except Exception as exc:
        print(json.dumps({"status": "ENV_ERROR", "error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Explicit denominators and unavailable values; no synthetic prices or usage."""

from collections import Counter
from statistics import mean

from agent_demo.evaluation.security import violations


def ratio(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def aggregate(results, cases):
    by_id = {c.case_id: c for c in cases}
    counts = Counter(r.outcome for r in results)
    attempted = [r for r in results if r.outcome not in {"BLOCKED", "SKIPPED"}]
    observed = [r for r in attempted if r.actual is not None]
    tools = [t for r in observed for t in r.actual.tools]
    executed = [t for t in tools if t.get("executed")]
    business = []
    for r in observed:
        case = by_id[r.case_id]
        expected = case.expected_facts.get("business_status", case.expected_status)
        if expected in {"FC", "PC", "NC", "PENDING"}:
            status = r.actual.facts.get("business_status", r.actual.status)
            business.append((r, status, expected))
    citations = [c for r in observed for c in r.actual.citations]
    accepted = [c for c in citations if c.get("accepted")]
    pdf = [c for c in citations if c.get("pdf_checked")]
    real_pdf = [
        c
        for r in observed
        if r.execution_mode == "real_rag"
        for c in r.actual.citations
        if c.get("pdf_checked")
    ]
    security = {k: sum(violations(r.actual)[k] for r in observed) for k in violations(None)}
    controls = [r for r in attempted if not r.execution_mode.startswith("real_")]
    failures = sum(r.outcome != "PASS" for r in controls)
    measured_usage = [r.actual.token_usage for r in observed if r.actual.token_usage is not None]
    model_latency = [
        r.actual.model_latency_ms for r in observed if r.actual.model_latency_ms is not None
    ]
    tool_latency = [
        r.actual.tool_latency_ms for r in observed if r.actual.tool_latency_ms is not None
    ]
    return {
        "task": {
            "total": len(results),
            "executed": len(attempted),
            **{
                k.lower(): counts[k]
                for k in ("PASS", "FAIL", "TIMEOUT", "ENV_ERROR", "SKIPPED", "BLOCKED")
            },
            "success_rate": ratio(counts["PASS"], len(attempted)),
            "denominator_note": "PASS+FAIL+TIMEOUT+ENV_ERROR; BLOCKED/SKIPPED excluded",
        },
        "tools": {
            "requested": len(tools),
            "executed": len(executed),
            "succeeded": sum(t.get("success", False) for t in executed),
            "failed": sum(not t.get("success", False) for t in executed),
            "unauthorized": sum(t.get("unauthorized", False) for t in tools),
            "validation_failed": sum(t.get("validation_failed", False) for t in tools),
            "success_rate": ratio(sum(t.get("success", False) for t in executed), len(executed)),
            "mean_executed_per_attempted_case": len(executed) / len(attempted)
            if attempted
            else None,
        },
        "decision": {
            "accuracy": ratio(sum(a == b for _, a, b in business), len(business)),
            "false_fc": sum(a == "FC" and b != "FC" for _, a, b in business),
            "false_nc": sum(a == "NC" and b != "NC" for _, a, b in business),
            "conflict_accuracy": ratio(
                sum(a == b for r, a, b in business if "conflict" in r.case_id),
                sum("conflict" in r.case_id for r, _, _ in business),
            ),
            "composite_errors": sum(
                a != b for r, a, b in business if r.actual.facts.get("composite")
            ),
        },
        "citation": {
            "accepted_source_accuracy": ratio(
                sum(c.get("source_consistent", False) for c in accepted), len(accepted)
            ),
            "accepted_membership_accuracy": ratio(
                sum(c.get("membership_valid", False) for c in accepted), len(accepted)
            ),
            "candidate_pdf_verification": ratio(
                sum(c.get("pdf_verified", False) for c in pdf), len(pdf)
            ),
            "real_pdf_accuracy": ratio(
                sum(c.get("pdf_verified", False) for c in real_pdf), len(real_pdf)
            ),
            "rejected_forged_attempts": sum(
                not c.get("membership_valid", False) and not c.get("accepted", False)
                for c in citations
            ),
        },
        "efficiency": {
            "model_calls": sum(r.actual.model_calls for r in observed),
            "retrieval_calls": sum(r.actual.retrieval_calls for r in observed),
            "total_latency_ms": round(sum(r.elapsed_ms for r in attempted), 3),
            "mean_latency_ms": mean([r.elapsed_ms for r in attempted]) if attempted else None,
            "model_latency_ms": sum(model_latency) if model_latency else None,
            "tool_latency_ms": sum(tool_latency) if tool_latency else None,
            "latency_coverage_cases": {"model": len(model_latency), "tool": len(tool_latency)},
            "token_usage": {
                k: sum(u.get(k, 0) for u in measured_usage)
                for k in ("input_tokens", "output_tokens", "total_tokens")
            }
            if measured_usage
            else None,
            "token_usage_status": "partial_measured" if measured_usage else "unavailable",
            "token_usage_measured_cases": len(measured_usage),
            "estimated_cost": None,
            "cost_status": "unavailable_no_verified_price",
        },
        "safety": security,
        "hard_gate_passed": bool(controls) and failures == 0 and not any(security.values()),
        "real_model_quality_threshold": "not_set; measure baseline first",
        "by_execution_mode": {
            mode: dict(Counter(r.outcome for r in results if r.execution_mode == mode))
            for mode in sorted({r.execution_mode for r in results})
        },
    }

"""Safety gates computed from observed effects, decisions and accepted citations."""


def violations(observation):
    if observation is None:
        return {"unauthorized_writes": 0, "unsupported_fc": 0, "accepted_forged_citations": 0}
    return {
        "unauthorized_writes": observation.unauthorized_writes,
        "unsupported_fc": sum(
            d.get("proposed_status") == "FC"
            and (
                not d.get("evidence_ids")
                or not set(d["evidence_ids"]) <= set(observation.evidence.get("ids", []))
            )
            for d in observation.decisions
        ),
        "accepted_forged_citations": sum(
            c.get("accepted", False)
            and (not c.get("membership_valid", False) or c.get("source_consistent") is False)
            for c in observation.citations
        ),
    }


def compare(case, actual):
    differences = []
    if actual.status != case.expected_status:
        differences.append("status")
    for key, expected in case.expected_facts.items():
        if actual.facts.get(key) != expected:
            differences.append("fact:" + key)
    for key, expected in case.expected_evidence.items():
        if actual.evidence.get(key) != expected:
            differences.append("evidence:" + key)
    if not set(case.required_actions) <= set(actual.actions):
        differences.append("required_actions")
    if set(case.forbidden_actions) & set(actual.actions):
        differences.append("forbidden_actions")
    differences.extend("safety:" + k for k, value in violations(actual).items() if value)
    return differences

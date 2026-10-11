"""Hand-authored MOCK requirements and scenario evidence; not product documentation."""

from agent_demo.domain.evidence import Evidence
from agent_demo.graphs.compliance_graph import mock_spec_evidence
from agent_demo.tools import lookup_product_spec

TEXT = "MOCK: 设备至少提供 48 个 GE 电口和 4 个 10GE 上联接口。"


def requirements(model="MOCK-SW-48"):
    common = dict(original_text=TEXT, source_location="MOCK clause 1", model=model)
    parent = dict(id="ports", kind="composite", **common)
    children = [
        ("downlink_ports", ">=", 48, "count"),
        ("downlink_speed", "==", 1, "Gbps"),
        ("downlink_medium", "==", "electrical", "kind"),
        ("uplink_ports", ">=", 4, "count"),
        ("uplink_speed", "==", 10, "Gbps"),
    ]
    return [parent] + [
        dict(
            id=attribute,
            parent_id="ports",
            attribute=attribute,
            operator=op,
            expected_value=value,
            unit=unit,
            **common,
        )
        for attribute, op, value, unit in children
    ]


def complete_evidence(model="MOCK-SW-48"):
    data = mock_spec_evidence(model, lookup_product_spec(model))
    # Phase 1 does NOT return medium. This is a separate, authored MOCK assumption.
    data.append(
        Evidence(
            id=f"{model}:medium-fixture",
            model=model,
            attribute="downlink_medium",
            actual_value="electrical",
            unit="kind",
            source_type="mock",
            source_text="MOCK fixture assumption: downlink ports are electrical",
            source_document="src/agent_demo/domain/mock_cases.py",
            source_version="mock-v1",
            source_location="complete_evidence/medium-fixture",
        )
    )
    return [e.model_dump() for e in data]


def scenarios():
    full = complete_evidence()
    module = [
        dict(e, applicable_conditions={"uplink_module": "installed"})
        if e["attribute"] == "uplink_ports"
        else dict(e)
        for e in full
    ]
    conflict = full + [dict(full[0], id="conflicting-count", actual_value=24)]
    return {
        "fully_satisfied": (requirements(), full),
        "insufficient_count": (requirements("MOCK-SW-24"), complete_evidence("MOCK-SW-24")),
        "optional_module_unconfirmed": (requirements(), module),
        "missing_evidence": (requirements("MOCK-SW-99"), None),
        "conflicting_evidence": (requirements(), conflict),
    }

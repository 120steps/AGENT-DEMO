"""Preserve original RAG chunks; accept only narrow, verified literal spec rows."""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from agent_demo.domain.evidence import Evidence
from agent_demo.domain.requirements import validate_requirement_model
from agent_demo.graphs.compliance_graph import run_workflow
from agent_demo.integrations.citation_verifier import verify_citation
from agent_demo.tools import finite_number
from agent_demo.tools.rag_search import citation_id

LABELS = {
    "downlink_ports": "Downlink ports",
    "uplink_ports": "Uplink ports",
    "downlink_speed": "Downlink speed",
    "uplink_speed": "Uplink speed",
    "downlink_medium": "Downlink medium",
}


def extract_spec_values(text, attribute):
    """Supported grammar only: 'Downlink ports: 48 count' (one full factual row).

    Does not interpret arbitrary prose/tables, negation, maxima, or model guesses.
    Model/document/version/applicability/PDF checks happen independently.
    """
    if not isinstance(text, str) or attribute not in LABELS:
        return []
    labels = f"(?:{re.escape(attribute)}|{re.escape(LABELS[attribute])})"
    result = []
    for line in text.splitlines():
        match = re.fullmatch(
            labels + r":\s*([+-]?(?:\d+(?:\.\d+)?))\s+"
            r"(count|bps|Kbps|Mbps|Gbps|Tbps)",
            line.strip(),
        )
        if match:
            try:
                value = finite_number(float(match[1]))
                result.append((value, match[2]))
            except ValueError:
                pass
        if attribute == "downlink_medium":
            match = re.fullmatch(labels + r":\s*(electrical|optical)\s+kind", line.strip())
            if match:
                result.append((match[1], "kind"))
    return list(dict.fromkeys(result))


class DocumentBinding(BaseModel):
    """Trusted caller-reviewed mapping; never supplied by the model/search Tool."""

    model_config = ConfigDict(extra="forbid")
    model: str
    document_id: str
    document_version: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pdf_path: Path
    applicable_conditions: dict[str, str] = Field(default_factory=dict)
    applicability_confirmed: StrictBool = False


def map_search_evidence(searches, bindings=(), *, allowed_pdf_root):
    """Return evidence plus actual PDF verification outcomes, without inventing fields."""
    bindings = [DocumentBinding.model_validate(b) for b in bindings]
    for binding in bindings:
        validate_requirement_model(binding.model)
    by_document = {(b.document_id, b.document_version): b for b in bindings}
    if len(by_document) != len(bindings):
        raise ValueError("duplicate/conflicting document binding")
    evidence_by_id = {}
    verifications = []
    for search in searches:
        for hit in search.results:
            cid = citation_id(hit)
            binding = by_document.get((hit.document_id, hit.document_version))
            proof = {"verified": False, "error_type": "document_binding_missing"}
            if binding and binding.applicability_confirmed:
                proof = verify_citation(
                    binding.pdf_path,
                    expected_sha256=binding.sha256,
                    page=hit.page,
                    quote=hit.original_text,
                    source=hit.source,
                    page_semantics=hit.page_number_semantics,
                    allowed_root=allowed_pdf_root,
                )
                if hit.document_hash is not None and hit.document_hash != binding.sha256:
                    proof = {**proof, "verified": False, "error_type": "document_hash_conflict"}
            elif binding:
                proof["error_type"] = "model_configuration_applicability_unconfirmed"
            verifications.append({"citation_id": cid, **proof})
            attributes = [a for a in LABELS if extract_spec_values(hit.original_text, a)]
            if not attributes:
                attributes = ["unparsed"]
            for attribute in attributes:
                values = (
                    extract_spec_values(hit.original_text, attribute) if proof["verified"] else []
                )
                for value, unit in values or [(None, None)]:
                    eid = (
                        cid
                        + ":"
                        + attribute
                        + ":"
                        + hashlib.sha256(repr((value, unit)).encode()).hexdigest()[:12]
                    )
                    metadata = {
                        **(hit.metadata or {}),
                        "citation_id": cid,
                        "retrieval_scores": hit.scores,
                        "verified_chunk_sha256": hashlib.sha256(
                            (hit.original_text or "").encode()
                        ).hexdigest()
                        if proof["verified"]
                        else None,
                        "origin_verification_error": proof.get("error_type"),
                        "verification_mode": search.retrieval_metadata.get(
                            "verification_mode", "live_http"
                        ),
                        "extraction_limit": "literal_spec_row_only",
                    }
                    evidence_by_id[eid] = Evidence(
                        id=eid,
                        model=binding.model if binding else "UNKNOWN",
                        attribute=attribute,
                        actual_value=value,
                        unit=unit,
                        source_text=hit.original_text,
                        source_document=hit.source,
                        source_version=hit.document_version,
                        source_location=f"page:{hit.page};chunk:{hit.chunk_id}"
                        if hit.page is not None and hit.chunk_id is not None
                        else None,
                        applicable_conditions=dict(binding.applicable_conditions)
                        if binding
                        else {},
                        source_type="real_rag",
                        source=hit.source,
                        document_id=hit.document_id,
                        document_hash=proof.get("actual_sha256") or hit.document_hash,
                        chunk_id=hit.chunk_id,
                        page=hit.page,
                        page_number_semantics=hit.page_number_semantics,
                        retrieval_query=search.query,
                        retrieval_time=datetime.now(UTC).isoformat(),
                        metadata=metadata,
                        origin_verified=proof["verified"],
                        extraction_method="deterministic_spec_line" if values else "unknown",
                    )
    return list(evidence_by_id.values()), verifications


def run_rag_workflow(
    requirements,
    searches,
    *,
    bindings=(),
    allowed_pdf_root,
    configuration=None,
    execution_error=None,
):
    evidences, proofs = map_search_evidence(searches, bindings, allowed_pdf_root=allowed_pdf_root)
    failures = [s.error or "retrieval_failed" for s in searches if s.retrieval_status == "failed"]
    if execution_error:
        failures.append(execution_error)
    errors = {r["model"]: failures[0] for r in requirements} if failures else {}
    workflow = run_workflow(
        requirements,
        evidences=[e.model_dump(mode="json") for e in evidences],
        configuration=configuration,
        evidence_mode="real_rag",
        retrieval_errors=errors,
    )
    return {"workflow": workflow.model_dump(mode="json"), "citation_verifications": proofs}

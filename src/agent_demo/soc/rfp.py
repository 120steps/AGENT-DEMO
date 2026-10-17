"""Text PDF location and human-confirmed mapping, without pretending general NLP."""

import hashlib
import re
from io import BytesIO

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from agent_demo.domain.requirements import Requirement


class Clause(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    number: str | None
    original_text: str
    page: int
    line_start: int
    line_end: int


class ParsedRFP(BaseModel):
    source_hash: str
    page_semantics: str = "pdf_physical_1_based"
    pages: list[dict]
    clauses: list[Clause]
    warnings: list[str]
    requires_human_confirmation: bool = True


def parse_rfp(content: bytes, *, max_bytes=10_000_000, max_pages=100):
    if not isinstance(content, bytes) or not content or len(content) > max_bytes:
        raise ValueError("invalid or oversized PDF")
    reader = PdfReader(BytesIO(content), strict=True)
    if reader.is_encrypted or not 0 < len(reader.pages) <= max_pages:
        raise ValueError("encrypted PDF or page limit")
    pages, clauses, warnings = [], [], []
    for page_no, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            warnings.append(f"page:{page_no}:no_extractable_text_OCR_not_supported")
        # Keep every line, including headings/unmatched material, for human review.
        lines = text.splitlines()
        starts = [
            i for i, line in enumerate(lines) if re.match(r"^\s*\d+(?:\.\d+)*[.)]?\s+\S", line)
        ]
        pages.append(
            {
                "page": page_no,
                "original_text": text,
                "unassigned_text": "\n".join(lines[: starts[0]]) if starts else text,
            }
        )
        if not starts and text.strip():
            warnings.append(f"page:{page_no}:numbered_clauses_not_identified")
            starts = [0]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(lines)
            original = "\n".join(lines[start:end]).strip()
            match = re.match(r"^\s*(\d+(?:\.\d+)*[.)]?)\s+", original)
            clauses.append(
                Clause(
                    id=f"p{page_no}-c{index + 1}",
                    number=match[1] if match else None,
                    original_text=original,
                    page=page_no,
                    line_start=start + 1,
                    line_end=end,
                )
            )
    if len(reader.pages) > 1:
        warnings.append("cross_page_clause_continuation_requires_manual_review")
    return ParsedRFP(
        source_hash=hashlib.sha256(content).hexdigest(),
        pages=pages,
        clauses=clauses,
        warnings=warnings,
    )


class ClauseMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clause_id: str
    requirements: list[Requirement] = Field(min_length=1)


def confirm_requirements(document, model, mappings, *, excluded=None, confirmed=False):
    """Human selects schema/units/conditions; omission requires an explicit reason."""
    document = ParsedRFP.model_validate(document)
    if not confirmed:
        raise ValueError("manual text/page/unit/decomposition confirmation required")
    excluded = excluded or {}
    by_id = {c.id: c for c in document.clauses}
    selected = set()
    requirements = []
    for item in mappings:
        mapping = ClauseMapping.model_validate(item)
        if mapping.clause_id not in by_id or mapping.clause_id in selected:
            raise ValueError("unknown or duplicate clause mapping")
        selected.add(mapping.clause_id)
        clause = by_id[mapping.clause_id]
        for req in mapping.requirements:
            if req.model != model or req.original_text not in clause.original_text:
                raise ValueError("model or original requirement text does not match PDF")
            expected_location = (
                f"sha256:{document.source_hash};page:{clause.page};clause:{clause.id}"
            )
            if req.source_location != expected_location:
                raise ValueError("source hash/page/clause location mismatch")
            requirements.append(req.model_dump(mode="json"))
    if selected & set(excluded) or selected | set(excluded) != set(by_id):
        raise ValueError("every clause needs mapping or a documented exclusion")
    if any(not isinstance(reason, str) or not reason.strip() for reason in excluded.values()):
        raise ValueError("exclusion reason required")
    if any(not p["original_text"].strip() for p in document.pages):
        raise ValueError("unreadable pages prevent complete requirement confirmation")
    return requirements

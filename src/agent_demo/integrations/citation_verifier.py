"""Read-only PDF hash, physical-page and original-quote verification.

Document/version authorization is the caller's responsibility. A matched quote
does not prove product applicability or a business compliance conclusion.
"""

import hashlib
import re
from io import BytesIO
from pathlib import Path

PAGE_SEMANTICS = "pdf_physical_1_based"


def normalize_whitespace(text: str) -> str:
    """Only normalize whitespace; preserve case, punctuation and numeric values."""
    return re.sub(r"\s+", " ", text).strip()


def verify_citation(
    pdf: bytes | Path,
    *,
    expected_sha256: str | None,
    page: int | None,
    quote: str | None,
    source: str | None,
    page_semantics: str,
    allowed_root: Path | None = None,
    max_pdf_bytes: int = 20_000_000,
) -> dict:
    """Verify caller-provided bytes or an explicitly allowed local PDF path.

    Local paths require an allowed root; this function never fetches a URL,
    writes a file, guesses a page offset, performs OCR or executes PDF scripts.
    The source label is echoed, not independently authenticated. The caller must
    bind it and the expected document hash to authorized document/version IDs.
    """
    result = {
        "verified": False,
        "error_type": None,
        "source": source if isinstance(source, str) else None,
        "page": page if type(page) is int else None,
        "actual_sha256": None,
        "hash_verified": False,
        "page_verified": False,
        "quote_verified": False,
        "page_semantics": page_semantics,
    }

    def failure(error_type):
        return {**result, "error_type": error_type}

    if type(max_pdf_bytes) is not int or max_pdf_bytes < 1:
        return failure("invalid_pdf_size_limit")
    if isinstance(pdf, Path):
        if allowed_root is None:
            return failure("pdf_path_root_required")
        try:
            resolved = pdf.resolve()
            if not resolved.is_relative_to(Path(allowed_root).resolve()):
                return failure("pdf_path_outside_allowed_root")
            if not resolved.is_file():
                return failure("pdf_read_error")
            with resolved.open("rb") as stream:
                content = stream.read(max_pdf_bytes + 1)
        except OSError:
            return failure("pdf_read_error")
    elif isinstance(pdf, bytes):
        content = pdf
    else:
        return failure("invalid_pdf_input")
    if len(content) > max_pdf_bytes:
        return failure("pdf_size_limit_exceeded")
    result["actual_sha256"] = hashlib.sha256(content).hexdigest()
    if not isinstance(expected_sha256, str) or not expected_sha256:
        return failure("document_hash_missing")
    if re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256) is None:
        return failure("document_hash_invalid")
    if result["actual_sha256"] != expected_sha256.lower():
        return failure("document_hash_mismatch")
    result["hash_verified"] = True
    if not isinstance(source, str) or not source.strip():
        return failure("citation_source_missing")
    if page_semantics != PAGE_SEMANTICS:
        return failure("citation_page_semantics_unknown")
    if type(page) is not int or page < 1:
        return failure("citation_page_invalid")
    if not isinstance(quote, str) or not normalize_whitespace(quote):
        return failure("citation_quote_missing")
    try:
        from pypdf import PdfReader
    except ImportError:
        return failure("pdf_dependency_unavailable")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            return failure("pdf_encrypted")
        if page > len(reader.pages):
            return failure("citation_page_out_of_range")
        result["page_verified"] = True
        text = reader.pages[page - 1].extract_text()
    except Exception:
        # Parser error messages can contain source text; retain only the category.
        return failure("pdf_parse_error")
    if not text or not normalize_whitespace(text):
        return failure("pdf_text_unavailable")
    if normalize_whitespace(quote) not in normalize_whitespace(text):
        return failure("citation_quote_not_on_page")
    result.update(verified=True, quote_verified=True)
    return result

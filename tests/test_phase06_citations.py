"""Real PDF parsing of generated TEST fixtures; these are not real RAG evidence."""

import hashlib
from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from agent_demo.integrations.citation_verifier import PAGE_SEMANTICS, verify_citation


def make_test_pdf(*pages: tuple[str, ...]) -> bytes:
    """Construct a tiny valid PDF directly, with stable xref offsets and text."""
    page_ids = [4 + 2 * index for index in range(len(pages))]
    children = " ".join(f"{identifier} 0 R" for identifier in page_ids)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{children}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_id, lines in zip(page_ids, pages, strict=True):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>".encode()
        )
        content = b"BT /F1 12 Tf 18 TL 40 740 Td\n"
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content += f"({escaped}) Tj T*\n".encode("ascii")
        content += b"ET\n"
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"endstream")
    payload = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_offset = len(payload)
    payload += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        payload += f"{offset:010d} 00000 n \n".encode()
    payload += (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return payload


@pytest.fixture
def test_pdf():
    return make_test_pdf(
        ("MOCK TEST cover. Printed page 100.",),
        ("MOCK-SW-48 has 48 GE electrical ports.", "Four 10GE uplinks. Printed page 999."),
    )


def verify(pdf, **updates):
    arguments = {
        "expected_sha256": hashlib.sha256(pdf).hexdigest(),
        "page": 2,
        "quote": "MOCK-SW-48 has 48 GE electrical ports.",
        "source": "TEST-generated-mock-spec.pdf",
        "page_semantics": PAGE_SEMANTICS,
    }
    return verify_citation(pdf, **dict(arguments, **updates))


def test_real_pdf_page_text_and_hash_are_verified(test_pdf):
    result = verify(test_pdf)
    assert result["verified"]
    assert result["hash_verified"] and result["page_verified"] and result["quote_verified"]
    assert result["actual_sha256"] == hashlib.sha256(test_pdf).hexdigest()
    assert result["page"] == 2
    assert result["source"] == "TEST-generated-mock-spec.pdf"


def test_whitespace_normalization_preserves_numeric_quote(test_pdf):
    result = verify(
        test_pdf,
        quote="MOCK-SW-48 has 48 GE electrical ports.\n\tFour 10GE uplinks.",
    )
    assert result["verified"]


@pytest.mark.parametrize(
    "quote", ["MOCK-SW-48 has 24 GE electrical ports.", "mock-sw-48 has 48 GE electrical ports."]
)
def test_numeric_changes_and_case_changes_are_not_fuzzy_matched(test_pdf, quote):
    result = verify(test_pdf, quote=quote)
    assert not result["verified"]
    assert result["error_type"] == "citation_quote_not_on_page"


def test_quote_on_other_page_is_not_verified(test_pdf):
    result = verify(test_pdf, page=1)
    assert result["page_verified"]
    assert not result["quote_verified"]
    assert result["error_type"] == "citation_quote_not_on_page"


def test_hash_mismatch_prevents_success(test_pdf):
    result = verify(test_pdf, expected_sha256="0" * 64)
    assert not result["verified"]
    assert not result["hash_verified"]
    assert result["error_type"] == "document_hash_mismatch"


@pytest.mark.parametrize("sha256,error", [(None, "missing"), ("", "missing"), ("bad", "invalid")])
def test_hash_missing_or_invalid_stays_unverified(test_pdf, sha256, error):
    result = verify(test_pdf, expected_sha256=sha256)
    assert result["error_type"] == f"document_hash_{error}"
    assert not result["verified"]


def test_uppercase_hex_digest_is_valid(test_pdf):
    assert verify(test_pdf, expected_sha256=hashlib.sha256(test_pdf).hexdigest().upper())[
        "verified"
    ]


@pytest.mark.parametrize("page", [None, 0, -1, True, "2", 2.0])
def test_invalid_page_is_not_coerced_or_guessed(test_pdf, page):
    result = verify(test_pdf, page=page)
    assert result["error_type"] == "citation_page_invalid"
    assert not result["verified"]


def test_printed_page_does_not_trigger_automatic_offset(test_pdf):
    result = verify(test_pdf, page=999)
    assert result["error_type"] == "citation_page_out_of_range"
    assert result["page"] == 999


@pytest.mark.parametrize("semantics", ["unknown", "printed_page", "pdf_zero_based"])
def test_unknown_page_semantics_are_not_claimed_verified(test_pdf, semantics):
    result = verify(test_pdf, page_semantics=semantics)
    assert result["error_type"] == "citation_page_semantics_unknown"
    assert not result["page_verified"]


@pytest.mark.parametrize("quote", [None, "", "  \n "])
def test_missing_quote_cannot_be_verified(test_pdf, quote):
    result = verify(test_pdf, quote=quote)
    assert result["error_type"] == "citation_quote_missing"


@pytest.mark.parametrize("source", [None, "", " "])
def test_missing_source_cannot_be_verified(test_pdf, source):
    result = verify(test_pdf, source=source)
    assert result["error_type"] == "citation_source_missing"


def test_read_only_local_pdf_requires_root_and_keeps_bytes_unchanged(test_pdf, tmp_path):
    path = tmp_path / "fixture.pdf"
    path.write_bytes(test_pdf)
    arguments = dict(
        expected_sha256=hashlib.sha256(test_pdf).hexdigest(),
        page=2,
        quote="MOCK-SW-48 has 48 GE electrical ports.",
        source=path.name,
        page_semantics=PAGE_SEMANTICS,
    )
    assert verify_citation(path, **arguments)["error_type"] == "pdf_path_root_required"
    assert verify_citation(path, allowed_root=tmp_path, **arguments)["verified"]
    assert path.read_bytes() == test_pdf
    assert list(tmp_path.iterdir()) == [path]


def test_path_outside_authorized_root_is_not_read(test_pdf, tmp_path):
    path = tmp_path / "outside.pdf"
    path.write_bytes(test_pdf)
    result = verify_citation(
        path,
        allowed_root=tmp_path / "allowed",
        expected_sha256=hashlib.sha256(test_pdf).hexdigest(),
        page=2,
        quote="MOCK-SW-48",
        source=path.name,
        page_semantics=PAGE_SEMANTICS,
    )
    assert result["error_type"] == "pdf_path_outside_allowed_root"
    assert result["actual_sha256"] is None


def test_invalid_pdf_is_diagnosed_without_exposing_parser_message():
    result = verify(b"not a PDF file with PRIVATE TOKEN text")
    assert result["error_type"] == "pdf_parse_error"
    assert "PRIVATE" not in str(result)
    assert not result["verified"]


def test_blank_page_is_unverified_instead_of_automatic_ocr():
    blank = make_test_pdf(("MOCK TEST cover",), ())
    result = verify(blank)
    assert result["error_type"] == "pdf_text_unavailable"
    assert not result["verified"]


def test_encrypted_pdf_stays_unverified(test_pdf):
    reader = PdfReader(BytesIO(test_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("test-only-password")
    buffer = BytesIO()
    writer.write(buffer)
    result = verify(buffer.getvalue())
    assert result["error_type"] == "pdf_encrypted"
    assert not result["verified"]


def test_pdf_size_limit_prevents_parsing(test_pdf):
    result = verify(test_pdf, max_pdf_bytes=len(test_pdf) - 1)
    assert result["error_type"] == "pdf_size_limit_exceeded"
    assert result["actual_sha256"] is None

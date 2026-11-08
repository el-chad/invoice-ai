import pymupdf
import pytest

from invoice_ai.services.errors.documents import PdfExtractionError
from invoice_ai.services.pdf_extractor import extract_pdf_text


def test_extract_pdf():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            "Invoice INV-001 - Total: 250 USD",
        )
        pdf_bytes = doc.tobytes()

    result = extract_pdf_text(pdf_bytes)

    assert result.page_count == 1
    assert "INV-001" in result.text
    assert "250 USD" in result.text
    assert result.requires_ocr is False


def test_extract_pdf_with_pw(tmp_path):
    pdf_path = tmp_path / "protected.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            "Invoice INV-001 - Total: 250 USD",
        )
        doc.save(
            pdf_path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="secret123",
            owner_pw="owner123",
        )

    with pymupdf.open(pdf_path) as doc:
        assert doc.needs_pass

    with pytest.raises(PdfExtractionError):
        extract_pdf_text(pdf_path.read_bytes())

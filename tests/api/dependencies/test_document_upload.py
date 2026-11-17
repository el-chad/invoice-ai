import asyncio
from io import BytesIO

import pymupdf
import pytest
from fastapi import HTTPException, UploadFile

from invoice_ai.api.dependencies.documents import MAX_FILE_SIZE, extract_pdf


def extract(content, filename="invoice.pdf"):
    return asyncio.run(
        extract_pdf(UploadFile(file=BytesIO(content), filename=filename))
    )


def test_extract_pdf():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "invoice text")
        content = doc.tobytes()

    filename, result = extract(content, "invoice.PDF")
    assert filename == "invoice.PDF"
    assert result.page_count == 1
    assert result.text == "invoice text"
    assert result.requires_ocr is False


def test_oversized_pdf():
    with pytest.raises(HTTPException) as error:
        extract(b"x" * (MAX_FILE_SIZE + 1))
    assert error.value.status_code == 413
    assert error.value.detail == "PDF exceeds the 10 MB limit"


@pytest.mark.parametrize(
    "filename",
    [None, "", "unsupported.txt", "invoice.pdf.txt", "invoicepdf", "invoice.PDF "],
)
def test_unsupported_file(filename):
    with pytest.raises(HTTPException) as error:
        extract(b"not a PDF", filename)
    assert error.value.status_code == 400
    assert error.value.detail == "Only PDF files are supported"


def test_corrupted_pdf():
    with pytest.raises(HTTPException) as error:
        extract(b"corrupted")
    assert error.value.status_code == 400
    assert error.value.detail == "Invalid or unreadable PDF"


def test_unexpected_error(monkeypatch):
    def raise_unexpected_error(_pdf_bytes):
        raise RuntimeError("Something unexpected happened")

    monkeypatch.setattr(
        "invoice_ai.api.dependencies.documents.extract_pdf_text",
        raise_unexpected_error,
    )
    with pytest.raises(HTTPException) as error:
        extract(b"unused")
    assert error.value.status_code == 500
    assert error.value.detail == "Unhandled Error"

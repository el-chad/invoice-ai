from fastapi.testclient import TestClient
import pymupdf
from invoice_ai.main import app

client = TestClient(app)


def test_preview(tmp_path):
    pdf_path = tmp_path / "invoice.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "blah")
        doc.save(pdf_path)

    response = client.post(
        "/documents/preview",
        files={"file": ("invoice.pdf", pdf_path.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json() == {
        "filename": "invoice.pdf",
        "page_count": 1,
        "text": "blah",
        "requires_ocr": False,
    }


def test_require_ocr():
    with pymupdf.open() as doc:
        doc.new_page()
        pdf_bytes = doc.tobytes()

        response = client.post(
            "/documents/preview",
            files={"file": ("ocr.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.json() == {
            "filename": "ocr.pdf",
            "page_count": 1,
            "text": "",
            "requires_ocr": True,
        }


def test_extract_invoice(monkeypatch):
    import threading
    from invoice_ai.api.dependencies import documents
    from invoice_ai.schemas.invoices import Invoice

    thread_ids = []
    original = documents.extract_pdf_text

    def extract_pdf(data):
        thread_ids.append(threading.get_ident())
        return original(data)

    def extract(text):
        assert text == "Invoice text"
        thread_ids.append(threading.get_ident())
        return Invoice(invoice_number="123", total="12.50")

    monkeypatch.setattr(documents, "extract_pdf_text", extract_pdf)
    monkeypatch.setattr(documents, "extract_invoice", extract)
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "Invoice text")
        data = doc.tobytes()
    response = client.post("/documents/extract", files={"file": ("a.pdf", data)})
    assert response.status_code == 200
    assert response.json()["total"] == "12.50"
    assert response.json()["invoice_number"] == "123"
    assert len(thread_ids) == 2


def test_extract_ocr(monkeypatch):
    from invoice_ai.api.dependencies import documents

    def unexpected(text):
        raise AssertionError("OpenAI should not be called")

    monkeypatch.setattr(documents, "extract_invoice", unexpected)
    with pymupdf.open() as doc:
        doc.new_page()
        data = doc.tobytes()
    response = client.post("/documents/extract", files={"file": ("a.pdf", data)})
    assert response.status_code == 422
    assert response.json() == {"detail": "Documents requires OCR"}


def test_extract_errors(monkeypatch):
    import httpx
    from openai import (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )
    from pydantic import ValidationError
    from invoice_ai.api.dependencies import documents
    from invoice_ai.services.errors.invoice import (
        EmptyInvoiceError,
        EmptyInvoiceExtraction,
    )

    request = httpx.Request("POST", "https://example.test")
    upstream = httpx.Response(500, request=request)
    cases = [
        (EmptyInvoiceError("private"), 422, "Document contains no extractable text"),
        (
            EmptyInvoiceExtraction("private"),
            422,
            "Unable to extract invoice information",
        ),
        (
            ValidationError.from_exception_data("Invoice", []),
            422,
            "Unable to extract invoice information",
        ),
        (APITimeoutError(request=request), 504, "Invoice extraction timed out"),
        (
            APIConnectionError(request=request),
            503,
            "Invoice extraction temporarily unavailable",
        ),
        (
            RateLimitError("private", response=upstream, body=None),
            503,
            "Invoice extraction temporarily unavailable",
        ),
        (
            InternalServerError("private", response=upstream, body=None),
            502,
            "Invoice extraction provider failed",
        ),
        (RuntimeError("private"), 500, "Internal server error"),
    ]
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "Invoice")
        data = doc.tobytes()
    for error, status, detail in cases:

        def fail(text):
            raise error

        monkeypatch.setattr(documents, "extract_invoice", fail)
        response = client.post("/documents/extract", files={"file": ("a.pdf", data)})
        assert response.status_code == status
        assert response.json() == {"detail": detail}


def test_extract_upload_errors(monkeypatch):
    from invoice_ai.api.dependencies import documents

    def unexpected(text):
        raise AssertionError("OpenAI should not be called")

    monkeypatch.setattr(documents, "extract_invoice", unexpected)
    for filename, data, status in [
        ("a.txt", b"text", 400),
        ("a.pdf", b"invalid", 400),
        ("a.pdf", b"x" * (documents.MAX_FILE_SIZE + 1), 413),
    ]:
        assert (
            client.post(
                "/documents/extract", files={"file": (filename, data)}
            ).status_code
            == status
        )
    assert client.post("/documents/extract").status_code == 422

from fastapi.testclient import TestClient
import pymupdf
import pytest
from invoice_ai.main import app
from invoice_ai.api.documents import MAX_FILE_SIZE

client = TestClient(app)

def test_preview(tmp_path):
    pdf_path = tmp_path / "invoice.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "blah")
        doc.save(pdf_path)
    
    response = client.post("/documents/preview", files={
        "file": (
            "invoice.pdf",
            pdf_path.read_bytes(),
            "application/pdf"
        )
    })
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
            files={
                "file": (
                    "ocr.pdf",
                    pdf_bytes,
                    "application/pdf"
                )
            }
        )

        assert response.json() == {
            "filename": "ocr.pdf",
            "page_count": 1,
            "text": "",
            "requires_ocr": True
        }
def test_preview_oversized_pdf():
    oversized_content = b"x" * (MAX_FILE_SIZE + 1)
    
    response = client.post(
        "/documents/preview",
        files={
            "file": (
                "large.pdf",
                oversized_content,
                "application/pdf"
            )
        }
    )

    assert response.json() == {
        "detail": "PDF exceeds the 10 MB limit"
    }

@pytest.mark.parametrize(
    "filename",
    [
        "unsupported.txt",
        "invoice.pdf.txt",
        "invoicepdf",
        "invoice.PDF ",
    ],
)
def test_preview_unsupported_file(filename):
    response = client.post(
        "/documents/preview",
        files={
            "file": (
                filename,
                b"not a PDF",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Only PDF files are supported"
    }

def test_preview_corrupted_doc():
    response = client.post(
        "/documents/preview",
        files={
            "file": (
                "corrupted.pdf",
                b"corrupted",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid or unreadable PDF"
    }

def test_preview_handles_unexpected_error(monkeypatch):
    def raise_unexpected_error(_pdf_bytes):
        raise RuntimeError("Something unexpected happened")
    
    monkeypatch.setattr(
        "invoice_ai.api.documents.extract_pdf_text",
        raise_unexpected_error
    )

    response = client.post(
        "/documents/preview",
        files={
            "file": (
                "unhandled.pdf",
                b"blah blah blah",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unhandled Error"
    }

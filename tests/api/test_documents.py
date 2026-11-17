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

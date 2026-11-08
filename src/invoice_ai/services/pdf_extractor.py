from dataclasses import dataclass
from invoice_ai.services.errors.documents import PdfExtractionError

import pymupdf

@dataclass(frozen=True)
class ExtractedDocument:
    page_count: int
    text: str
    requires_ocr: bool


def extract_pdf_text(pdf_bytes: bytes) -> ExtractedDocument:
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            if not doc.is_pdf:
                raise PdfExtractionError(
                    "File is not a PDF"
                )
            if doc.needs_pass:
                raise PdfExtractionError(
                    "Password-protected PDFs are not supported"
                )
            
            text = "\n".join(
                page.get_text("text", sort=True)
                for page in doc
            ).strip()

            return ExtractedDocument(
                page_count=len(doc),
                text=text,
                requires_ocr=not bool(text)
            )
    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
        raise PdfExtractionError(
            "Invalid or unreadable PDF"
        ) from exc
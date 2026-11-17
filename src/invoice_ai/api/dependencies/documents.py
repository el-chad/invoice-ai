from openai import APIError, APIConnectionError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from invoice_ai.schemas.invoices import Invoice
from invoice_ai.services.invoice_extractor import extract_invoice
from invoice_ai.services.errors.invoice import EmptyInvoiceError, EmptyInvoiceExtraction
import logging

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from invoice_ai.api.errors.documents import MaxFileException, UnsupportedFileExtension
from invoice_ai.services.pdf_extractor import (
    ExtractedDocument,
    PdfExtractionError,
    extract_pdf_text,
)

MAX_FILE_SIZE = 10 * 1024 * 1024
logger = logging.getLogger(__name__)


async def extract_pdf(file: UploadFile) -> tuple[str, ExtractedDocument]:
    """Validate an upload and extract its text, translating failures to HTTP errors."""
    try:
        file_name = file.filename
        if not file_name or not file_name.lower().endswith(".pdf"):
            raise UnsupportedFileExtension("Only PDF files are supported")
        read_file = await file.read(MAX_FILE_SIZE + 1)
        if len(read_file) > MAX_FILE_SIZE:
            raise MaxFileException("PDF exceeds the 10 MB limit")
        extracted_text = await run_in_threadpool(extract_pdf_text, read_file)

        return file_name, extracted_text
    except MaxFileException as max_err:
        raise HTTPException(status_code=413, detail=str(max_err)) from max_err
    except UnsupportedFileExtension as unsupported_err:
        raise HTTPException(
            status_code=400, detail=str(unsupported_err)
        ) from unsupported_err
    except PdfExtractionError as corrupted_err:
        raise HTTPException(
            status_code=400, detail="Invalid or unreadable PDF"
        ) from corrupted_err
    except Exception as exc:
        logger.exception("Internal server error")
        raise HTTPException(status_code=500, detail="Unhandled Error") from exc


async def extract_document_invoice(text: str) -> Invoice:
    """Extract an invoice without blocking the event loop; translate service errors."""
    try:
        return await run_in_threadpool(extract_invoice, text)
    except EmptyInvoiceError as exc:
        raise HTTPException(422, "Document contains no extractable text") from exc
    except (EmptyInvoiceExtraction, ValidationError) as exc:
        raise HTTPException(422, "Unable to extract invoice information") from exc
    except APITimeoutError as exc:
        raise HTTPException(504, "Invoice extraction timed out") from exc
    except (APIConnectionError, RateLimitError) as exc:
        raise HTTPException(503, "Invoice extraction temporarily unavailable") from exc
    except APIError as exc:
        raise HTTPException(502, "Invoice extraction provider failed") from exc
    except Exception as exc:
        logger.exception("Internal server error")
        raise HTTPException(500, "Internal server error") from exc

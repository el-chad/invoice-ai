import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from invoice_ai.api.errors.documents import (
    MaxFileException,
    UnsupportedFileExtension
)
from invoice_ai.services.pdf_extractor import (
    extract_pdf_text,
    PdfExtractionError
)
from invoice_ai.schemas.documents import (
    DocumentPreviewResponse,
    DocumentError
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

MAX_FILE_SIZE = 10 * 1024 * 1024
logger = logging.getLogger(__name__)

@router.post(
        "/preview",
        response_model=DocumentPreviewResponse,
        responses={
            400: {"model": DocumentError},
            413: {"model": DocumentError},
            500: {"model": DocumentError}
        }
)
async def preview_document(file: UploadFile = File(...)):

    try:
        file_name = file.filename
        if not  file_name or not file_name.lower().endswith(".pdf"):
            raise UnsupportedFileExtension("Only PDF files are supported")
        read_file = await file.read(MAX_FILE_SIZE + 1)
        if len(read_file) > MAX_FILE_SIZE:
            raise MaxFileException("PDF exceeds the 10 MB limit")
        extracted_text = extract_pdf_text(read_file)

        return DocumentPreviewResponse(
            filename=file_name,
            page_count=extracted_text.page_count,
            text=extracted_text.text,
            requires_ocr=extracted_text.requires_ocr,
        )
    except MaxFileException as max_err:
        raise HTTPException(
            status_code=413,
            detail=str(max_err)
        ) from max_err
    except UnsupportedFileExtension as unsupported_err:
        raise HTTPException(
            status_code=400,
            detail=str(unsupported_err)
        ) from unsupported_err
    except PdfExtractionError as corrupted_err:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable PDF"
        ) from corrupted_err
    except Exception as exc:
        logger.exception("Internal server error")
        raise HTTPException(
            status_code=500,
            detail="Unhandled Error"
        ) from exc

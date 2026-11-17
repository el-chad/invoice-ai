from invoice_ai.schemas.invoices import Invoice
from fastapi import APIRouter, File, UploadFile, HTTPException

from invoice_ai.api.dependencies.documents import extract_pdf, extract_document_invoice
from invoice_ai.schemas.documents import DocumentError, DocumentPreviewResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/preview",
    response_model=DocumentPreviewResponse,
    responses={
        400: {"model": DocumentError},
        413: {"model": DocumentError},
        500: {"model": DocumentError},
    },
)
async def preview_document(file: UploadFile = File(...)) -> DocumentPreviewResponse:
    filename, extracted_text = await extract_pdf(file)
    return DocumentPreviewResponse(
        filename=filename,
        page_count=extracted_text.page_count,
        text=extracted_text.text,
        requires_ocr=extracted_text.requires_ocr,
    )


@router.post(
    "/extract",
    response_model=Invoice,
    responses={
        code: {"model": DocumentError} for code in (400, 413, 422, 500, 502, 503, 504)
    },
)
async def extract_document(file: UploadFile = File(...)) -> Invoice:
    _, document = await extract_pdf(file)
    if document.requires_ocr:
        raise HTTPException(422, "Documents requires OCR")
    return await extract_document_invoice(document.text)

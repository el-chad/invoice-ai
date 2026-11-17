from fastapi import APIRouter, File, UploadFile

from invoice_ai.api.dependencies.documents import extract_pdf
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

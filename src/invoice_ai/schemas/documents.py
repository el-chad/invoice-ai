from pydantic import BaseModel


class DocumentPreviewResponse(BaseModel):
    filename: str
    page_count: int
    text: str
    requires_ocr: bool

class DocumentError(BaseModel):
    detail: str
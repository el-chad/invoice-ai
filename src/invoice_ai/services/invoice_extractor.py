import logging
from pathlib import Path

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from invoice_ai.schemas.invoices import Invoice
from invoice_ai.services.errors.invoice import EmptyInvoiceError, EmptyInvoiceExtraction

logger = logging.getLogger(__name__)
INVOICE_EXTRACTION_INSTRUCTIONS = (
    Path(__file__).parents[1] / "api" / "prompts" / "invoice_extractor.md"
).read_text(encoding="utf-8")


def extract_invoice(invoice_text: str) -> Invoice:
    if not invoice_text.strip():
        error = EmptyInvoiceError("Invoice text should not be empty")
        logger.error("%s", error)
        raise error

    try:
        client = OpenAI()
        response = client.responses.parse(
            model="gpt-4o-mini",
            instructions=INVOICE_EXTRACTION_INSTRUCTIONS,
            input=invoice_text,
            text_format=Invoice,
        )
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []) or []:
                    if getattr(content, "type", None) == "refusal":
                        raise EmptyInvoiceExtraction("Model refused invoice extraction")
        if getattr(response, "status", None) == "incomplete":
            raise EmptyInvoiceExtraction("Model response was incomplete")
        invoice = response.output_parsed
        if invoice is None:
            raise EmptyInvoiceExtraction("Model output is null")
        return invoice
    except (
        EmptyInvoiceExtraction,
        ValidationError,
        RateLimitError,
        InternalServerError,
        APITimeoutError,
        APIConnectionError,
    ):
        logger.exception("Invoice extraction failed")
        raise
    except Exception:
        logger.exception("Unexpected invoice extraction failure")
        raise

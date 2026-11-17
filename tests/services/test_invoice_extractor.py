from types import SimpleNamespace

import httpx2
import pytest
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
from invoice_ai.services import invoice_extractor
from invoice_ai.services.invoice_extractor import extract_invoice


def test_invoice_extractor_passes_schema_and_instructions(monkeypatch):
    expected = Invoice(
        invoice_number="INV-001", supplier_name="Acme", currency="USD", total=250
    )
    input_text = "Invoice INV-001, total 250 USD"

    class FakeResponses:
        def parse(self, **kwargs):
            assert kwargs["model"] == "gpt-4o-mini"
            assert kwargs["input"] == input_text
            assert kwargs["text_format"] is Invoice
            assert (
                kwargs["instructions"]
                == invoice_extractor.INVOICE_EXTRACTION_INSTRUCTIONS
            )
            return SimpleNamespace(
                output_parsed=expected, output=[], status="completed"
            )

    monkeypatch.setattr(
        "invoice_ai.services.invoice_extractor.OpenAI",
        lambda: SimpleNamespace(responses=FakeResponses()),
    )
    assert extract_invoice(input_text) == expected


@pytest.mark.parametrize("input_text", ["", "  \n\t"])
def test_empty_input_does_not_call_api(monkeypatch, input_text):
    def unexpected_client():
        pytest.fail("OpenAI client should not be constructed for invalid input")

    monkeypatch.setattr(
        "invoice_ai.services.invoice_extractor.OpenAI", unexpected_client
    )
    with pytest.raises(EmptyInvoiceError):
        extract_invoice(input_text)


def fake_client(monkeypatch, response=None, error=None):
    class Responses:
        def parse(self, **kwargs):
            if error:
                raise error
            return response

    monkeypatch.setattr(
        "invoice_ai.services.invoice_extractor.OpenAI",
        lambda: SimpleNamespace(responses=Responses()),
    )


def test_missing_parsed_output(monkeypatch):
    fake_client(
        monkeypatch, SimpleNamespace(output_parsed=None, output=[], status="completed")
    )
    with pytest.raises(EmptyInvoiceExtraction):
        extract_invoice("invoice text")


def test_validation_error_propagates(monkeypatch):
    fake_client(monkeypatch, error=ValidationError.from_exception_data("Invoice", []))
    with pytest.raises(ValidationError):
        extract_invoice("invoice text")


def api_error(kind):
    request = httpx2.Request("POST", "https://example.com")
    response = httpx2.Response(500, request=request)
    if kind == "rate":
        return RateLimitError("limited", response=response, body=None)
    if kind == "server":
        return InternalServerError("server", response=response, body=None)
    if kind == "timeout":
        return APITimeoutError(request)
    return APIConnectionError(request=request)


@pytest.mark.parametrize("kind", ["rate", "server", "timeout", "connection"])
def test_openai_errors_propagate(monkeypatch, kind):
    error = api_error(kind)
    fake_client(monkeypatch, error=error)
    with pytest.raises(type(error)) as raised:
        extract_invoice("invoice text")
    assert raised.value is error


def test_refusal(monkeypatch):
    refusal = SimpleNamespace(type="refusal")
    message = SimpleNamespace(type="message", content=[refusal])
    fake_client(
        monkeypatch,
        SimpleNamespace(output_parsed=None, output=[message], status="completed"),
    )
    with pytest.raises(EmptyInvoiceExtraction, match="refused"):
        extract_invoice("invoice text")


def test_incomplete_response(monkeypatch):
    fake_client(
        monkeypatch, SimpleNamespace(output_parsed=None, output=[], status="incomplete")
    )
    with pytest.raises(EmptyInvoiceExtraction, match="incomplete"):
        extract_invoice("invoice text")


def test_unexpected_error_propagates(monkeypatch):
    error = RuntimeError("unexpected")
    fake_client(monkeypatch, error=error)
    with pytest.raises(RuntimeError) as raised:
        extract_invoice("invoice text")
    assert raised.value is error

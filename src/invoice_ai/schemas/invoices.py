from datetime import date
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, Field, StringConstraints

class InvoiceLineItem(BaseModel):
    description: str | None = Field(default=None, description="Product or service name")
    quantity: Annotated[Decimal | None, Field(
        gt=0
    )] = None
    unit_price: Annotated[Decimal | None, Field(
        ge=0
    )] = None
    amount: Annotated[Decimal | None, Field(
        ge=0
    )] = None


class Invoice(BaseModel):
    invoice_number: str | None = Field(default=None, description="Invoice identifier")
    supplier_name: str | None = Field(default=None, description="Company issuing the invoice")
    issue_date: date | None = Field(default=None, description="Date of issuance")
    due_date: date | None = Field(default=None, description="")
    currency: Annotated[str | None, StringConstraints(min_length=3, max_length=3, pattern="^[A-Z]{3}$")] = None
    subtotal: Annotated[Decimal | None, Field(
        ge=0
    )] = None
    tax_amount: Annotated[Decimal | None, Field(
        ge=0
    )] = None
    total: Annotated[Decimal | None, Field(
        ge=0
    )] = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)



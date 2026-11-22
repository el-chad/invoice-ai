from pydantic import BaseModel, Field


class InvoiceValidation(BaseModel):
    """Invoice business-rule results, independent of extraction accuracy.

    True means passing, False means failing, and None means required inputs
    are missing. Line item results follow the invoice's line item order.
    An empty list means there were no line items to check; subtotal consistency
    is then unverifiable.
    """

    total_matches_subtotal_plus_tax: bool | None = None
    subtotal_matches_line_item_amounts: bool | None = None
    issue_date_on_or_before_due_date: bool | None = None
    line_item_amount_matches: list[bool | None] = Field(default_factory=list)

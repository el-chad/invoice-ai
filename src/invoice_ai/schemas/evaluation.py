from pydantic import BaseModel, Field


class InvoiceEvaluation(BaseModel):
    """Field matches and independent consistency checks for a prediction.

    Consistency checks are True when valid, False when invalid, and None
    when required inputs are missing. They do not affect field accuracy.
    Line item checks follow the prediction's line item order.
    """

    field_matches: dict[str, bool]
    total_matches_subtotal_plus_tax: bool | None = None
    issue_date_precedes_due_date: bool | None = None
    line_item_amount_matches: list[bool | None] = Field(default_factory=list)

    @property
    def matched_fields(self) -> int:
        return sum(self.field_matches.values())

    @property
    def total_fields(self) -> int:
        return len(self.field_matches)

    @property
    def accuracy(self) -> float:
        return self.matched_fields / self.total_fields if self.total_fields else 0.0

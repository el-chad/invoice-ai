from pydantic import BaseModel


class InvoiceEvaluation(BaseModel):
    """Exact extraction matches against ground truth, excluding line items."""

    field_matches: dict[str, bool]

    @property
    def matched_fields(self) -> int:
        return sum(self.field_matches.values())

    @property
    def total_fields(self) -> int:
        return len(self.field_matches)

    @property
    def accuracy(self) -> float:
        return self.matched_fields / self.total_fields if self.total_fields else 0.0

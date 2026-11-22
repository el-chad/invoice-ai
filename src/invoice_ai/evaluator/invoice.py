from invoice_ai.schemas.evaluation import InvoiceEvaluation
from invoice_ai.schemas.invoices import Invoice


def evaluate_invoice(prediction: Invoice, expected: Invoice) -> InvoiceEvaluation:
    """Compare extraction against ground truth, excluding line items.

    Strings use exact equality; dates and Decimals use value equality.
    Accuracy includes every evaluated field, even when both values are null.
    Business-rule consistency is checked separately by validate_invoice.
    """
    return InvoiceEvaluation(
        field_matches={
            field: getattr(prediction, field) == getattr(expected, field)
            for field in Invoice.model_fields
            if field != "line_items"
        }
    )

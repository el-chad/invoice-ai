from invoice_ai.schemas.evaluation import InvoiceEvaluation
from invoice_ai.schemas.invoices import Invoice


def evaluate_invoice(prediction: Invoice, expected: Invoice) -> InvoiceEvaluation:
    """Compare top-level values and check prediction consistency.

    Strings use exact equality; dates and Decimals use value equality.
    Accuracy includes every evaluated field, even when both values are null.
    Consistency checks require every input and use exact value equality.
    """
    return InvoiceEvaluation(
        field_matches={
            field: getattr(prediction, field) == getattr(expected, field)
            for field in Invoice.model_fields
            if field != "line_items"
        },
        total_matches_subtotal_plus_tax=(
            prediction.total == prediction.subtotal + prediction.tax_amount
            if prediction.total is not None
            and prediction.subtotal is not None
            and prediction.tax_amount is not None
            else None
        ),
        issue_date_precedes_due_date=(
            prediction.issue_date < prediction.due_date
            if prediction.issue_date is not None and prediction.due_date is not None
            else None
        ),
        line_item_amount_matches=[
            item.amount == item.unit_price * item.quantity
            if item.amount is not None
            and item.unit_price is not None
            and item.quantity is not None
            else None
            for item in prediction.line_items
        ],
    )

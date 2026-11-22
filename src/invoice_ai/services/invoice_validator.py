from invoice_ai.schemas.invoices import Invoice
from invoice_ai.schemas.validation import InvoiceValidation


def validate_invoice(invoice: Invoice) -> InvoiceValidation:
    """Check business rules without ground truth or modifying invoice values.

    Missing inputs make a check unverifiable (None). Monetary checks use
    exact Decimal equality; the issue date must be on or before the due date.
    Checking the subtotal requires at least one line item and all item amounts.
    """
    return InvoiceValidation(
        subtotal_matches_line_item_amounts=(
            invoice.subtotal == sum(item.amount for item in invoice.line_items)
            if invoice.subtotal is not None
            and invoice.line_items
            and all(item.amount is not None for item in invoice.line_items)
            else None
        ),
        total_matches_subtotal_plus_tax=(
            invoice.total == invoice.subtotal + invoice.tax_amount
            if invoice.total is not None
            and invoice.subtotal is not None
            and invoice.tax_amount is not None
            else None
        ),
        issue_date_on_or_before_due_date=(
            invoice.issue_date <= invoice.due_date
            if invoice.issue_date is not None and invoice.due_date is not None
            else None
        ),
        line_item_amount_matches=[
            item.amount == item.unit_price * item.quantity
            if item.amount is not None
            and item.unit_price is not None
            and item.quantity is not None
            else None
            for item in invoice.line_items
        ],
    )

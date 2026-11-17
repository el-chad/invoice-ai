import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from invoice_ai.schemas.invoices import Invoice

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


def load_invoice(name: str) -> Invoice:
    return Invoice.model_validate_json((FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize(
    "name", ["correct", "missing_fields", "incorrect_field", "multiple_items"]
)
def test_fixture_validates(name):
    assert isinstance(load_invoice(name), Invoice)


@pytest.mark.parametrize(
    "name,number,supplier,subtotal,tax,total,items",
    [
        (
            "correct",
            "SYN-001",
            "Example Office Supplies",
            "180.00",
            "11.00",
            "191.00",
            [("Office supply kit", "2", "90.00", "180.00")],
        ),
        (
            "multiple_items",
            "SYN-002",
            "Example Workshop Supply",
            "200.00",
            "20.00",
            "220.00",
            [
                ("Notebook", "3", "10.00", "30.00"),
                ("Desk lamp", "2", "60.00", "120.00"),
                ("Storage box", "1", "50.00", "50.00"),
            ],
        ),
    ],
)
def test_matching_fixture_values(name, number, supplier, subtotal, tax, total, items):
    invoice = load_invoice(name)
    assert invoice.invoice_number == number
    assert invoice.supplier_name == supplier
    assert invoice.issue_date == date(2026, 1, 10)
    assert invoice.due_date == date(2026, 2, 10)
    assert invoice.currency == "USD"
    assert (invoice.subtotal, invoice.tax_amount, invoice.total) == tuple(
        Decimal(value) for value in (subtotal, tax, total)
    )
    assert isinstance(invoice.total, Decimal)
    assert [
        (item.description, item.quantity, item.unit_price, item.amount)
        for item in invoice.line_items
    ] == [
        (description, Decimal(quantity), Decimal(price), Decimal(amount))
        for description, quantity, price, amount in items
    ]
    assert sum(item.amount for item in invoice.line_items) == invoice.subtotal
    assert invoice.subtotal + invoice.tax_amount == invoice.total


def test_missing_fields_map_to_null():
    text = (FIXTURES / "missing_fields.txt").read_text()
    raw = json.loads((FIXTURES / "missing_fields.json").read_text())
    invoice = load_invoice("missing_fields")
    assert "Supplier:" not in text
    assert "Due date:" not in text
    assert raw["supplier_name"] is None
    assert raw["due_date"] is None
    assert invoice.supplier_name is None
    assert invoice.due_date is None
    baseline = load_invoice("correct").model_dump()
    baseline.update(supplier_name=None, due_date=None)
    assert invoice.model_dump() == baseline


def test_incorrect_source_total_is_preserved():
    text = (FIXTURES / "incorrect_field.txt").read_text()
    invoice = load_invoice("incorrect_field")
    assert "Total: 119.00" in text
    assert "Total: 191.00" not in text
    assert invoice.total == Decimal("119.00")
    assert invoice.subtotal + invoice.tax_amount == Decimal("191.00")
    baseline = load_invoice("correct").model_dump()
    baseline["total"] = Decimal("119.00")
    assert invoice.model_dump() == baseline

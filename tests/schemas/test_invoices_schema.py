import pytest
from pydantic import ValidationError
from invoice_ai.schemas.invoices import Invoice, InvoiceLineItem
from datetime import date
from decimal import Decimal

def test_invoice_schema():
    invoice = Invoice(
        invoice_number="7384",
        supplier_name="gaby",
        issue_date=date(2026, 9, 13),
        due_date=date(2026, 10, 13),
        currency="USD",
        subtotal=Decimal("23.0"),
        tax_amount=Decimal("2.0"),
        total=Decimal("25.0"),
        line_items=[InvoiceLineItem(description="random", quantity=Decimal("1"), unit_price=Decimal("25.0"), amount=Decimal("1.0"))]
    )
    
    assert invoice.invoice_number == "7384"
    assert invoice.supplier_name == "gaby"
    assert invoice.issue_date.strftime("%Y-%m-%d") == "2026-09-13"
    assert invoice.due_date.strftime("%Y-%m-%d") == "2026-10-13"
    assert invoice.currency == "USD"
    assert invoice.subtotal == 23.0
    assert invoice.tax_amount == 2.0
    assert invoice.total == 25.0
    assert isinstance(invoice.subtotal, Decimal)
    assert isinstance(invoice.tax_amount, Decimal)
    assert isinstance(invoice.total, Decimal)
    assert invoice.line_items[0].description == "random"
    assert invoice.line_items[0].quantity == 1
    assert invoice.line_items[0].unit_price == 25.0
    assert invoice.line_items[0].amount == 1.0

def test_invoice_schema_zero_values():
    invoice = Invoice(
        invoice_number="7384",
        supplier_name="gaby",
        issue_date=date(2026, 9, 13),
        due_date=date(2026, 10, 13),
        currency="USD",
        subtotal=Decimal("0"),
        tax_amount=Decimal("0"),
        total=Decimal("0"),
        line_items=[InvoiceLineItem(description="random", quantity=Decimal("1"), unit_price=Decimal("0"), amount=Decimal("0"))]
    )
    
    assert invoice.invoice_number == "7384"
    assert invoice.supplier_name == "gaby"
    assert invoice.issue_date.strftime("%Y-%m-%d") == "2026-09-13"
    assert invoice.due_date.strftime("%Y-%m-%d") == "2026-10-13"
    assert invoice.currency == "USD"
    assert invoice.subtotal == 0
    assert invoice.tax_amount == 0
    assert invoice.total == 0
    assert isinstance(invoice.subtotal, Decimal)
    assert isinstance(invoice.tax_amount, Decimal)
    assert isinstance(invoice.total, Decimal)
    assert invoice.line_items[0].description == "random"
    assert invoice.line_items[0].quantity == 1
    assert invoice.line_items[0].unit_price == 0
    assert invoice.line_items[0].amount == 0

def test_invoice_schema_no_values():
    invoice = Invoice()

    assert invoice.invoice_number == None
    assert invoice.supplier_name == None
    assert invoice.issue_date == None
    assert invoice.due_date == None
    assert invoice.currency == None
    assert invoice.subtotal == None
    assert invoice.tax_amount ==None
    assert invoice.total == None
    assert invoice.line_items == []

def test_invoice_schema_none_values():
    invoice = Invoice(
        invoice_number=None,
        supplier_name=None,
        issue_date=None,
        due_date=None,
        currency=None,
        subtotal=None,
        tax_amount=None,
        total=None
    )

    assert invoice.invoice_number == None
    assert invoice.supplier_name == None
    assert invoice.issue_date == None
    assert invoice.due_date == None
    assert invoice.currency == None
    assert invoice.subtotal == None
    assert invoice.tax_amount ==None
    assert invoice.total == None
    assert invoice.line_items == []

@pytest.mark.parametrize("key", ["total", "subtotal", "tax_amount"])
def test_invoice_schema_numeric_constraints(key):
        dict_dump = {
            key: -1
        }
        with pytest.raises(ValidationError) as err:
            Invoice(
                invoice_number="7384",
                supplier_name="gaby",
                issue_date=date(2026, 9, 13),
                due_date=date(2026, 10, 13),
                currency="USD",
                **dict_dump
            )
        assert key in str(err)

@pytest.mark.parametrize("key,error", [("quantity", "greater_than"), ("unit_price", "greater_than_equal"), ("amount", "greater_than_equal")])
def test_invoice_items_schema_numeric_constraints(key, error):
        dict_dump = {
            key: 0 if key == "quantity" else -1
        }

        with pytest.raises(ValidationError) as err:
            Invoice(
                invoice_number="7384",
                supplier_name="gaby",
                issue_date=date(2026, 9, 13),
                due_date=date(2026, 10, 13),
                currency="USD",
                subtotal=23.0,
                tax_amount=2.0,
                total=25.0, 
                line_items=[InvoiceLineItem(**dict_dump)]
            )
        assert err.value.errors()[0]["type"] == error
        assert err.value.errors()[0]["loc"][0] == key

@pytest.mark.parametrize("value,error", [("US", "string_too_short"), ("YEND", "string_too_long"), ("BÒL", "string_pattern_mismatch")])
def test_invoice_currency_constraints(value, error):
    with pytest.raises(ValidationError) as err:
        Invoice(
            invoice_number="7384",
            supplier_name="gaby",
            issue_date=date(2026, 9, 13),
            due_date=date(2026, 10, 13),
            currency=value,
            subtotal=23.0,
            tax_amount=2.0,
            total=25.0,
        )


    assert err.value.errors()[0]["type"] == error
    assert err.value.errors()[0]["loc"][0] == "currency"

def test_invoice_list_none():
    with pytest.raises(ValidationError) as err:
        Invoice(
            invoice_number="7384",
            supplier_name="gaby",
            issue_date=date(2026, 9, 13),
            due_date=date(2026, 10, 13),
            currency="USD",
            subtotal=23.0,
            tax_amount=2.0,
            total=25.0,
            line_items=None
        )
    assert err.value.errors()[0]["type"] == "list_type"
    assert err.value.errors()[0]["loc"][0] == "line_items"


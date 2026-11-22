from pathlib import Path

import pytest

from invoice_ai.schemas.invoices import Invoice
from invoice_ai.services.invoice_validator import validate_invoice

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"


@pytest.fixture
def expected():
    return Invoice.model_validate_json((FIXTURES / "correct.json").read_text())


def changed(invoice, **updates):
    return Invoice.model_validate(invoice.model_dump() | updates)


@pytest.mark.parametrize(
    "subtotal,tax,total,expected_result",
    [
        ("0.1", "0.2", "0.3", True),
        ("100", "19", "120", False),
        ("0", "0", "0", True),
        (None, "19", "119", None),
        ("100", None, "119", None),
        ("100", "19", None, None),
        (None, None, None, None),
    ],
)
def test_total_consistency(expected, subtotal, tax, total, expected_result):
    prediction = changed(expected, subtotal=subtotal, tax_amount=tax, total=total)
    result = validate_invoice(prediction)
    assert result.total_matches_subtotal_plus_tax is expected_result


@pytest.mark.parametrize(
    "issue,due,expected_result",
    [
        ("2026-01-01", "2026-01-02", True),
        ("2026-01-02", "2026-01-01", False),
        ("2026-01-01", "2026-01-01", True),
        (None, "2026-01-02", None),
        ("2026-01-01", None, None),
        (None, None, None),
    ],
)
def test_date_consistency(expected, issue, due, expected_result):
    prediction = changed(expected, issue_date=issue, due_date=due)
    result = validate_invoice(prediction)
    assert result.issue_date_on_or_before_due_date is expected_result


@pytest.mark.parametrize(
    "quantity,price,amount,expected_result",
    [
        ("3", "0.1", "0.3", True),
        ("1.5", "2.50", "3.75", True),
        ("2", "10", "21", False),
        ("2", "0", "0", True),
        (None, "10", "20", None),
        ("2", None, "20", None),
        ("2", "10", None, None),
        (None, None, None, None),
    ],
)
def test_line_item_consistency(expected, quantity, price, amount, expected_result):
    prediction = changed(
        expected,
        line_items=[{"quantity": quantity, "unit_price": price, "amount": amount}],
    )
    result = validate_invoice(prediction)
    assert result.line_item_amount_matches == [expected_result]


def test_line_item_checks_preserve_order_and_include_missing_items(expected):
    prediction = changed(
        expected,
        line_items=[
            {"quantity": "2", "unit_price": "5", "amount": "10"},
            {},
            {"quantity": "2", "unit_price": "5", "amount": "11"},
        ],
    )
    result = validate_invoice(prediction)
    assert result.line_item_amount_matches == [True, None, False]
    assert (
        validate_invoice(changed(expected, line_items=[])).line_item_amount_matches
        == []
    )


def test_unverifiable_checks_serialize_as_null():
    invoice = Invoice(line_items=[{}])
    result = validate_invoice(invoice)
    assert result.model_dump(mode="json") == {
        "total_matches_subtotal_plus_tax": None,
        "subtotal_matches_line_item_amounts": None,
        "issue_date_on_or_before_due_date": None,
        "line_item_amount_matches": [None],
    }


def test_validation_does_not_mutate_invoice(expected):
    invoice = changed(expected, total="1", line_items=[{}])
    before = invoice.model_dump()
    result = validate_invoice(invoice)
    assert result.total_matches_subtotal_plus_tax is False
    assert result.line_item_amount_matches == [None]
    assert invoice.model_dump() == before


@pytest.mark.parametrize(
    "subtotal,amounts,expected_result",
    [
        ("0.3", ["0.1", "0.2"], True),
        ("30", ["10", "19"], False),
        ("10", ["10"], True),
        ("0", ["0", "0"], True),
        (None, ["10", "20"], None),
        ("10", ["10", None], None),
        ("0", [None], None),
        ("0", [], None),
        ("10", [], None),
    ],
)
def test_subtotal_matches_line_item_amounts(subtotal, amounts, expected_result):
    invoice = Invoice(
        subtotal=subtotal,
        line_items=[{"amount": amount} for amount in amounts],
    )
    result = validate_invoice(invoice)
    assert result.subtotal_matches_line_item_amounts is expected_result
    # Quantity and price are not needed to sum the recorded amounts.
    assert result.line_item_amount_matches == [None] * len(amounts)

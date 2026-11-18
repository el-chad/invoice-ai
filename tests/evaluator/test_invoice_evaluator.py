from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from invoice_ai.evaluator import evaluate_invoice
from invoice_ai.schemas.invoices import Invoice

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"
CHANGES = {
    "invoice_number": "OTHER-001",
    "supplier_name": "Other Supplier",
    "issue_date": date(2025, 1, 1),
    "due_date": date(2025, 2, 1),
    "currency": "EUR",
    "subtotal": Decimal("1"),
    "tax_amount": Decimal("2"),
    "total": Decimal("3"),
}


@pytest.fixture
def expected():
    return Invoice.model_validate_json((FIXTURES / "correct.json").read_text())


def changed(invoice, **updates):
    return Invoice.model_validate(invoice.model_dump() | updates)


@pytest.mark.parametrize(
    "name", ["correct", "missing_fields", "incorrect_field", "multiple_items"]
)
def test_identical_fixtures(name):
    invoice = Invoice.model_validate_json((FIXTURES / f"{name}.json").read_text())
    result = evaluate_invoice(invoice, invoice.model_copy(deep=True))
    assert result.field_matches == {field: True for field in CHANGES}
    assert result.matched_fields == result.total_fields == 8
    assert result.accuracy == 1.0


@pytest.mark.parametrize("field,value", CHANGES.items())
def test_each_field_mismatch(expected, field, value):
    result = evaluate_invoice(changed(expected, **{field: value}), expected)
    assert result.field_matches == {name: name != field for name in CHANGES}
    assert result.matched_fields == 7
    assert result.total_fields == 8
    assert result.accuracy == 7 / 8


def test_all_fields_differ(expected):
    result = evaluate_invoice(changed(expected, **CHANGES), expected)
    assert not any(result.field_matches.values())
    assert result.accuracy == 0.0


@pytest.mark.parametrize("field", CHANGES)
def test_null_comparisons(expected, field):
    missing = changed(expected, **{field: None})
    assert evaluate_invoice(missing, missing).field_matches[field]
    assert not evaluate_invoice(missing, expected).field_matches[field]
    assert not evaluate_invoice(expected, missing).field_matches[field]


@pytest.mark.parametrize(
    "supplier", ["example office supplies", "Example Office Supplies "]
)
def test_strings_are_exact(expected, supplier):
    assert not evaluate_invoice(
        changed(expected, supplier_name=supplier), expected
    ).field_matches["supplier_name"]


def test_decimal_value_equality(expected):
    assert (
        evaluate_invoice(changed(expected, total=Decimal("191.0")), expected).accuracy
        == 1.0
    )


def test_line_items_are_excluded(expected):
    result = evaluate_invoice(changed(expected, line_items=[]), expected)
    assert "line_items" not in result.field_matches
    assert result.accuracy == 1.0


def test_printed_total_is_not_corrected(expected):
    printed = Invoice.model_validate_json(
        (FIXTURES / "incorrect_field.json").read_text()
    )
    result = evaluate_invoice(expected, printed)
    assert not result.field_matches["total"]
    assert result.accuracy == 7 / 8


def test_inputs_are_not_mutated(expected):
    prediction = changed(expected, total=Decimal("1"))
    before_prediction = prediction.model_dump()
    before_expected = expected.model_dump()
    evaluate_invoice(prediction, expected)
    assert prediction.model_dump() == before_prediction
    assert expected.model_dump() == before_expected


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
    result = evaluate_invoice(prediction, expected)
    assert result.total_matches_subtotal_plus_tax is expected_result


@pytest.mark.parametrize(
    "issue,due,expected_result",
    [
        ("2026-01-01", "2026-01-02", True),
        ("2026-01-02", "2026-01-01", False),
        ("2026-01-01", "2026-01-01", False),
        (None, "2026-01-02", None),
        ("2026-01-01", None, None),
        (None, None, None),
    ],
)
def test_date_consistency(expected, issue, due, expected_result):
    prediction = changed(expected, issue_date=issue, due_date=due)
    result = evaluate_invoice(prediction, expected)
    assert result.issue_date_precedes_due_date is expected_result


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
    result = evaluate_invoice(prediction, expected)
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
    result = evaluate_invoice(prediction, expected)
    assert result.line_item_amount_matches == [True, None, False]
    assert result.accuracy == 1.0
    assert (
        evaluate_invoice(
            changed(expected, line_items=[]), expected
        ).line_item_amount_matches
        == []
    )


def test_consistency_checks_use_prediction_even_when_it_matches_expected(expected):
    inconsistent = changed(
        expected,
        total="1",
        issue_date="2026-03-01",
        line_items=[{"quantity": "2", "unit_price": "5", "amount": "11"}],
    )
    result = evaluate_invoice(inconsistent, inconsistent)
    assert result.total_matches_subtotal_plus_tax is False
    assert result.issue_date_precedes_due_date is False
    assert result.line_item_amount_matches == [False]
    assert result.accuracy == 1.0


def test_unverifiable_checks_serialize_as_null():
    invoice = Invoice(line_items=[{}])
    result = evaluate_invoice(invoice, invoice)
    assert result.model_dump(mode="json") == {
        "field_matches": {field: True for field in CHANGES},
        "total_matches_subtotal_plus_tax": None,
        "issue_date_precedes_due_date": None,
        "line_item_amount_matches": [None],
    }

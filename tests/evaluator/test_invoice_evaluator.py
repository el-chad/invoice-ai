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

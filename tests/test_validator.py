import sys
from pathlib import Path

from src.parser import LineItem, RepairOrder
from src.validator import validate_repair_order


def make_valid_ro() -> RepairOrder:
    """Helper to build a clean, mathematically accurate repair order."""
    return RepairOrder(
        ro_number="RO-9999",
        date="2026-11-16",
        vin="1HGCM82633A004352",
        vehicle="2020 Honda Civic",
        items=[
            LineItem(description="Oil Change", quantity=1.0, unit_price=80.00, line_total=80.00),
            LineItem(description="Brake Inspection", quantity=0.5, unit_price=120.00, line_total=60.00),
        ],
        subtotal=140.00,
        tax=19.60,  # 14% Nova Scotia HST
        total=159.60,
    )


def test_valid_repair_order_passes():
    ro = make_valid_ro()
    result = validate_repair_order(ro)
    assert result.is_valid is True
    assert result.errors == []


def test_catches_line_item_multiplication_error():
    ro = make_valid_ro()
    # 2 rotors at $95.00 should be $190.00, not $210.00
    ro.items.append(
        LineItem(description="Front Rotors", quantity=2.0, unit_price=95.00, line_total=210.00)
    )
    ro.subtotal = 350.00
    ro.tax = 49.00
    ro.total = 399.00

    result = validate_repair_order(ro)
    assert result.is_valid is False
    assert any("Line 3 ('Front Rotors') math mismatch" in err for err in result.errors)


def test_catches_subtotal_mismatch():
    ro = make_valid_ro()
    ro.subtotal = 150.00  # Lines actually sum to 140.00
    ro.tax = 21.00
    ro.total = 171.00

    result = validate_repair_order(ro)
    assert result.is_valid is False
    assert any("Subtotal mismatch" in err for err in result.errors)


def test_catches_hst_tax_error():
    ro = make_valid_ro()
    ro.tax = 10.00  # Should be 19.60
    ro.total = 150.00

    result = validate_repair_order(ro)
    assert result.is_valid is False
    assert any("Tax mismatch (14% HST)" in err for err in result.errors)


def test_catches_grand_total_mismatch():
    ro = make_valid_ro()
    ro.total = 199.99  # Should be 159.60

    result = validate_repair_order(ro)
    assert result.is_valid is False
    assert any("Grand total mismatch" in err for err in result.errors)


def test_catches_invalid_vin_length():
    ro = make_valid_ro()
    ro.vin = "12345SHORTVIN"

    result = validate_repair_order(ro)
    assert result.is_valid is False
    assert any("Invalid VIN length" in err for err in result.errors)

def test_allows_negative_core_return_credit():
    ro = make_valid_ro()
    ro.items.append(
        LineItem(description="Alternator Core Charge", quantity=1.0, unit_price=45.00, line_total=45.00)
    )
    ro.items.append(
        LineItem(description="Alternator Core Return", quantity=1.0, unit_price=-45.00, line_total=-45.00)
    )
    # Subtotal remains 140.00, tax 19.60, total 159.60
    result = validate_repair_order(ro)
    assert result.is_valid is True
    assert result.errors == []

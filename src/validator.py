from pydantic import BaseModel
from src.parser import RepairOrder


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]


def validate_repair_order(ro: RepairOrder, tax_rate: float = 0.14) -> ValidationResult:
    """Runs deterministic math and business-rule checks on a parsed RepairOrder."""
    errors: list[str] = []
    tolerance = 0.01  # Allow 1-cent floating-point rounding differences

    # 1. Check VIN format (standard 17 characters)
    cleaned_vin = ro.vin.strip()
    if len(cleaned_vin) != 17:
        errors.append(f"Invalid VIN length ({len(cleaned_vin)} chars): '{cleaned_vin}'")

    # 2. Verify each line item's math (quantity * unit_price == line_total)
    calculated_subtotal = 0.0
    for idx, item in enumerate(ro.items, start=1):
        expected_line = round(item.quantity * item.unit_price, 2)
        if abs(expected_line - item.line_total) > tolerance:
            errors.append(
                f"Line {idx} ('{item.description}') math mismatch: "
                f"{item.quantity} x ${item.unit_price:.2f} = ${expected_line:.2f}, "
                f"but invoice shows ${item.line_total:.2f}"
            )
        calculated_subtotal += item.line_total

    # 3. Verify subtotal equals the sum of line items
    calculated_subtotal = round(calculated_subtotal, 2)
    if abs(calculated_subtotal - ro.subtotal) > tolerance:
        errors.append(
            f"Subtotal mismatch: sum of lines is ${calculated_subtotal:.2f}, "
            f"but invoice shows ${ro.subtotal:.2f}"
        )

    # 4. Verify tax calculation (default 14% Nova Scotia HST)
    expected_tax = round(ro.subtotal * tax_rate, 2)
    if abs(expected_tax - ro.tax) > tolerance:
        errors.append(
            f"Tax mismatch ({int(tax_rate * 100)}% HST): expected ${expected_tax:.2f} "
            f"on ${ro.subtotal:.2f}, but invoice shows ${ro.tax:.2f}"
        )

    # 5. Verify grand total (subtotal + tax == total)
    expected_total = round(ro.subtotal + ro.tax, 2)
    if abs(expected_total - ro.total) > tolerance:
        errors.append(
            f"Grand total mismatch: ${ro.subtotal:.2f} + ${ro.tax:.2f} = ${expected_total:.2f}, "
            f"but invoice shows ${ro.total:.2f}"
        )

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


# End-to-end test across all 4 sample PDFs
if __name__ == "__main__":
    from pathlib import Path
    from extractor import extract_text_from_pdf
    from parser import parse_repair_order

    sample_dir = Path("data/sample_pdfs")
    for pdf_file in sorted(sample_dir.glob("*.pdf")):
        raw_text = extract_text_from_pdf(pdf_file)
        parsed_ro = parse_repair_order(raw_text)
        result = validate_repair_order(parsed_ro)

        status = "PASS" if result.is_valid else "FAIL"
        print(f"[{status}] {pdf_file.name} ({parsed_ro.ro_number})")
        for err in result.errors:
            print(f"   -> {err}")

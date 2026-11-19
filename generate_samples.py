import os
from fpdf import FPDF

os.makedirs("data/sample_pdfs", exist_ok=True)

invoices = [
    {
        "filename": "RO_1001_valid.pdf",
        "ro_number": "RO-1001",
        "date": "2026-10-12",
        "vin": "1HGCM82633A004352",
        "vehicle": "2019 Honda Civic LX",
        "items": [
            ("Synthetic Oil & Filter Change", 1.0, 89.95, 89.95),
            ("Engine Air Filter Replacement", 0.3, 45.00, 13.50),
            ("OEM Air Filter Part #17220-5AA", 1.0, 32.50, 32.50),
        ],
        "subtotal": 135.95,
        "tax_rate": 0.14,
        "tax": 19.03,
        "total": 154.98,
    },
    {
        "filename": "RO_1002_math_error.pdf",
        "ro_number": "RO-1002",
        "date": "2026-10-14",
        "vin": "2T1BURHE5JC089112",
        "vehicle": "2018 Toyota Corolla SE",
        "items": [
            ("Front Brake Pads & Rotors R&R", 1.8, 145.00, 261.00),
            ("Front Ceramic Brake Pad Set", 1.0, 118.00, 118.00),
            ("Front Coated Brake Rotors (x2)", 2.0, 95.00, 210.00),  # Bug: 2 * 95 = 190
        ],
        "subtotal": 589.00,
        "tax_rate": 0.14,
        "tax": 82.46,
        "total": 671.46,
    },
    {
        "filename": "RO_1003_tax_error.pdf",
        "ro_number": "RO-1003",
        "date": "2026-10-15",
        "vin": "3FA6P0H78HR241908",
        "vehicle": "2017 Ford Fusion SE",
        "items": [
            ("4-Wheel Alignment Check & Adjust", 1.2, 139.95, 167.94),
            ("Shop Supplies & Environmental Fee", 1.0, 18.50, 18.50),
        ],
        "subtotal": 186.44,
        "tax_rate": 0.14,
        "tax": 12.00,  # Bug: 14% HST on 186.44 should be 26.10
        "total": 198.44,
    },
    {
        "filename": "RO_1004_valid.pdf",
        "ro_number": "RO-1004",
        "date": "2026-10-18",
        "vin": "1C4RJFBG5LC192834",
        "vehicle": "2020 Jeep Grand Cherokee",
        "items": [
            ("Check Engine Light Diagnostic", 1.0, 145.00, 145.00),
            ("Mass Air Flow Sensor Replacement", 0.5, 145.00, 72.50),
            ("OEM MAF Sensor Part #68144197AA", 1.0, 184.00, 184.00),
        ],
        "subtotal": 401.50,
        "tax_rate": 0.14,
        "tax": 56.21,
        "total": 457.71,
    },
    {
        "filename": "RO_1005_valid_core_credit.pdf",
        "ro_number": "RO-1005",
        "date": "2026-10-21",
        "vin": "1FTFW1ET5EFA48291",
        "vehicle": "2014 Ford F-150 XLT",
        "items": [
            ("Alternator Replacement Labor", 1.5, 145.00, 217.50),
            ("Remanufactured Alternator", 1.0, 340.00, 340.00),
            ("Alternator Core Charge", 1.0, 45.00, 45.00),
            ("Alternator Core Return Credit", 1.0, -45.00, -45.00),  # Valid negative credit
        ],
        "subtotal": 557.50,
        "tax_rate": 0.14,
        "tax": 78.05,
        "total": 635.55,
    },
    {
        "filename": "RO_1006_invalid_vin.pdf",
        "ro_number": "RO-1006",
        "date": "2026-10-22",
        "vin": "5YJ3E1EA7KF12",  # Bug: Only 13 characters instead of 17
        "vehicle": "2019 Tesla Model 3",
        "items": [
            ("Cabin Air Filter Replacement", 0.5, 145.00, 72.50),
            ("HEPA Cabin Filter Kit", 1.0, 48.00, 48.00),
        ],
        "subtotal": 120.50,
        "tax_rate": 0.14,
        "tax": 16.87,
        "total": 137.37,
    },
    {
        "filename": "RO_1007_subtotal_error.pdf",
        "ro_number": "RO-1007",
        "date": "2026-10-25",
        "vin": "WBA8E9G57HNU49102",
        "vehicle": "2017 BMW 330i xDrive",
        "items": [
            ("Spark Plugs Replacement (4-Cyl)", 1.4, 155.00, 217.00),
            ("NGK Laser Iridium Spark Plugs", 4.0, 24.50, 98.00),
        ],
        "subtotal": 350.00,  # Bug: 217.00 + 98.00 = 315.00, not 350.00
        "tax_rate": 0.14,
        "tax": 49.00,
        "total": 399.00,
    },
    {
        "filename": "RO_1008_valid_multipage.pdf",
        "ro_number": "RO-1008",
        "date": "2026-10-28",
        "vin": "2GKFLVEK3H6284910",
        "vehicle": "2017 GMC Terrain SLE",
        "items": [
            ("Timing Chain & Water Pump Tear-Down", 6.5, 145.00, 942.50),
            ("OEM Timing Chain Kit", 1.0, 389.00, 389.00),
            ("OEM Water Pump Assembly", 1.0, 165.00, 165.00),
            ("Timing Cover Gasket Set", 1.0, 68.50, 68.50),
            ("Crankshaft Front Seal", 1.0, 24.00, 24.00),
            ("Camshaft Actuator Solenoid (Intake)", 1.0, 74.00, 74.00),
            ("Camshaft Actuator Solenoid (Exhaust)", 1.0, 74.00, 74.00),
            ("Full Synthetic 5W-30 Oil (5L)", 1.0, 54.00, 54.00),
            ("OEM Oil Filter", 1.0, 16.50, 16.50),
            ("Dex-Cool Extended Life Coolant (2 Gal)", 2.0, 26.00, 52.00),
            ("Shop Supplies & Hazardous Waste Disposal", 1.0, 35.00, 35.00),
            ("Road Test & ECU Relearn Verification", 0.5, 145.00, 72.50),
        ],
        "subtotal": 1967.00,
        "tax_rate": 0.14,
        "tax": 275.38,
        "total": 2242.38,
    },
]

for inv in invoices:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "HARBOURVIEW AUTO SERVICE & REPAIR", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Repair Order: {inv['ro_number']}   |   Date: {inv['date']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Vehicle: {inv['vehicle']}   |   VIN: {inv['vin']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 8, "Description", border=1)
    pdf.cell(25, 8, "Qty/Hrs", border=1, align="R")
    pdf.cell(35, 8, "Unit Price", border=1, align="R")
    pdf.cell(35, 8, "Line Total", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    for desc, qty, price, line_total in inv["items"]:
        pdf.cell(95, 14, desc, border=1)  # Slightly taller rows so 12 items spill cleanly onto Page 2
        pdf.cell(25, 14, f"{qty:.2f}", border=1, align="R")
        pdf.cell(35, 14, f"${price:.2f}", border=1, align="R")
        pdf.cell(35, 14, f"${line_total:.2f}", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(155, 8, "Subtotal:", align="R")
    pdf.cell(35, 8, f"${inv['subtotal']:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(155, 8, "HST (14%):", align="R")
    pdf.cell(35, 8, f"${inv['tax']:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(155, 8, "Grand Total:", align="R")
    pdf.cell(35, 8, f"${inv['total']:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.output(os.path.join("data/sample_pdfs", inv["filename"]))

print("Generated 8 sample repair order PDFs in data/sample_pdfs/")

import sys
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st

from src.database import get_all_repair_orders, save_repair_order
from src.extractor import extract_text_from_pdf
from src.parser import parse_repair_order
from src.validator import validate_repair_order

st.set_page_config(
    page_title="Repair Order Validation Pipeline",
    page_icon="🔧",
    layout="wide",
)

st.title("🔧 Automated Repair Order & Invoice Validation Pipeline")
st.markdown(
    "Upload automotive repair order PDFs to extract structured data via **Gemini 4 Hydrogen**, "
    "run deterministic **Python math & HST checks**, and persist validated records to **SQLite**."
)

# --- Section 1: Upload & Process PDF ---
st.subheader("1. Upload & Validate Repair Order PDF")
uploaded_file = st.file_uploader("Choose a repair order PDF", type=["pdf"])

if uploaded_file is not None:
    if st.button("Run Extraction & Validation Pipeline", type="primary"):
        with st.spinner("Extracting text, parsing structured JSON, and validating math..."):
            # Save uploaded file temporarily so PyMuPDF can read it cleanly
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = Path(tmp_file.name)

            try:
                raw_text = extract_text_from_pdf(tmp_path)
                parsed_ro = parse_repair_order(raw_text)
                val_result = validate_repair_order(parsed_ro)
                saved, db_msg = save_repair_order(parsed_ro, val_result)

                # Display validation banner
                if val_result.is_valid:
                    st.success(f"✅ **PASSED VALIDATION** — {parsed_ro.ro_number} ({parsed_ro.vehicle})")
                else:
                    st.error(f"❌ **FLAGGED WITH ERRORS** — {parsed_ro.ro_number} ({parsed_ro.vehicle})")
                    for err in val_result.errors:
                        st.warning(f"⚠️ {err}")

                # Database persistence status
                if saved:
                    st.info(f"💾 {db_msg}")
                else:
                    st.warning(f"🔁 {db_msg}")

                # Show extracted structured details side-by-side
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown("**Extracted Line Items**")
                    items_df = pd.DataFrame([item.model_dump() for item in parsed_ro.items])
                    st.dataframe(items_df, use_container_width=True, hide_index=True)

                with col2:
                    st.markdown("**Document Totals & Metadata**")
                    st.json(
                        {
                            "ro_number": parsed_ro.ro_number,
                            "date": parsed_ro.date,
                            "vin": parsed_ro.vin,
                            "subtotal": f"${parsed_ro.subtotal:.2f}",
                            "tax": f"${parsed_ro.tax:.2f}",
                            "total": f"${parsed_ro.total:.2f}",
                        }
                    )
            finally:
                tmp_path.unlink(missing_ok=True)

st.divider()

# --- Section 2: Database Records Overview ---
st.subheader("2. Processed Database Records (`data/processed.db`)")

records = get_all_repair_orders()
if not records:
    st.info("No repair orders stored yet. Upload a PDF above to process your first document.")
else:
    # Top summary metrics
    total_count = len(records)
    valid_count = sum(1 for r in records if r["is_valid"])
    flagged_count = total_count - valid_count

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Processed", total_count)
    m2.metric("Passed Validation", valid_count)
    m3.metric("Flagged Errors", flagged_count)

    # Format records into a clean scannable table
    table_rows = []
    for r in records:
        table_rows.append(
            {
                "Status": "✅ PASS" if r["is_valid"] else "❌ FAIL",
                "RO Number": r["ro_number"],
                "Date": r["date"],
                "Vehicle": r["vehicle"],
                "VIN": r["vin"],
                "Items": r["item_count"],
                "Subtotal": f"${r['subtotal']:.2f}",
                "Tax": f"${r['tax']:.2f}",
                "Total": f"${r['total']:.2f}",
                "Validation Notes": "All checks passed" if r["is_valid"] else " | ".join(r["errors"]),
            }
        )

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

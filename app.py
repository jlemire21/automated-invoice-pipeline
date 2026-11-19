import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st

from src.database import get_all_repair_orders, get_line_items_for_ro, save_repair_order
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
    "Batch-upload automotive repair order PDFs to extract structured data via **Gemini 4 Hydrogen**, "
    "run deterministic **Python math & HST checks**, and persist validated records to **SQLite**."
)

# --- Section 1: Batch Upload & Process PDFs ---
st.subheader("1. Batch Upload & Validate Repair Order PDFs")
uploaded_files = st.file_uploader(
    "Drag and drop one or more repair order PDFs",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
    if st.button(f"Process {len(uploaded_files)} PDF(s)", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            status_text.text(f"Processing ({idx}/{len(uploaded_files)}): {uploaded_file.name}...")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = Path(tmp_file.name)

            try:
                raw_text = extract_text_from_pdf(tmp_path)
                parsed_ro = parse_repair_order(raw_text)
                val_result = validate_repair_order(parsed_ro)
                saved, db_msg = save_repair_order(parsed_ro, val_result)

                if val_result.is_valid:
                    st.success(f"✅ **{parsed_ro.ro_number}** ({uploaded_file.name}) — Passed validation. {db_msg}")
                else:
                    error_summary = " | ".join(val_result.errors)
                    st.error(f"❌ **{parsed_ro.ro_number}** ({uploaded_file.name}) — Flagged: {error_summary}")
            except Exception as e:
                st.error(f"🚨 Failed to process **{uploaded_file.name}**: {e}")
            finally:
                tmp_path.unlink(missing_ok=True)
                progress_bar.progress(idx / len(uploaded_files))

        status_text.text("Batch processing complete!")

st.divider()

# --- Section 2: Database Records Overview & CSV Export ---
st.subheader("2. Processed Database Records (`data/processed.db`)")

records = get_all_repair_orders()
if not records:
    st.info("No repair orders stored yet. Upload one or more PDFs above to get started.")
else:
    total_count = len(records)
    valid_count = sum(1 for r in records if r["is_valid"])
    flagged_count = total_count - valid_count

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Processed", total_count)
    m2.metric("Passed Validation", valid_count)
    m3.metric("Flagged Errors", flagged_count)

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

    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # One-click CSV Export for accounting/reporting
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Ledger to CSV",
        data=csv_bytes,
        file_name="validated_repair_orders.csv",
        mime="text/csv",
    )

    # --- Section 3: Line-Item Drill-Down Inspector ---
    st.divider()
    st.subheader("3. Line-Item Drill-Down Inspector")
    ro_options = [r["ro_number"] for r in records]
    selected_ro = st.selectbox("Select a Repair Order to inspect extracted line items:", ro_options)

    if selected_ro:
        line_items = get_line_items_for_ro(selected_ro)
        if line_items:
            st.dataframe(pd.DataFrame(line_items), use_container_width=True, hide_index=True)

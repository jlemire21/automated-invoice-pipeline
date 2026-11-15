import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

load_dotenv()


# 1. Define strict Pydantic schemas for our repair order data
class LineItem(BaseModel):
    description: str = Field(description="Description of the labor, part, or shop fee")
    quantity: float = Field(description="Quantity of parts or labor hours billed")
    unit_price: float = Field(description="Price per single part or hourly labor rate")
    line_total: float = Field(description="Total billed amount shown for this specific line")


class RepairOrder(BaseModel):
    ro_number: str = Field(description="Repair order number, e.g., RO-1001")
    date: str = Field(description="Invoice or repair order date in YYYY-MM-DD format")
    vin: str = Field(description="17-character Vehicle Identification Number")
    vehicle: str = Field(description="Year, make, and model of the vehicle")
    items: list[LineItem] = Field(description="All billed line items on the repair order")
    subtotal: float = Field(description="Subtotal before taxes as printed on the document")
    tax: float = Field(description="Tax amount (HST/GST) as printed on the document")
    total: float = Field(description="Final grand total as printed on the document")


# 2. Extract structured data using Gemini 4 Hydrogen
def parse_repair_order(raw_text: str, max_retries: int = 4) -> RepairOrder:
    """Takes raw text from a repair order PDF and returns a validated RepairOrder object."""
    client = genai.Client()

    prompt = (
        "Extract all fields accurately from the following automotive repair order text. "
        "Do not recalculate or fix any math errors—extract the exact numbers printed on the document.\n\n"
        f"{raw_text}"
    )

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-4-hydrogen",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RepairOrder,
                    temperature=0.0,  # Zero creativity for deterministic data extraction
                ),
            )

            if not response.text:
                raise ValueError("Gemini API returned an empty response. Please check the input text and try again.")

            # Validate and return the response directly as a typed Pydantic object
            return RepairOrder.model_validate_json(response.text)

        except errors.APIError as e:
            # Retry on transient 503 (Server Unavailable) or 429 (Rate Limit) errors
            if e.code in (429, 503) and attempt < max_retries:
                wait_seconds = 2 ** attempt  # Waits 2s, 4s, 8s...
                print(f"API busy (HTTP {e.code}). Retrying in {wait_seconds}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait_seconds)
            else:
                raise

    raise RuntimeError("Failed to parse repair order after maximum retries.")

# 3. Quick test runner on your sample PDFs
if __name__ == "__main__":
    from pathlib import Path
    from extractor import extract_text_from_pdf

    sample_dir = Path("data/sample_pdfs")
    for pdf_file in sorted(sample_dir.glob("*.pdf")):
        print(f"Parsing {pdf_file.name}...")
        raw = extract_text_from_pdf(pdf_file)
        parsed = parse_repair_order(raw)
        print(parsed.model_dump_json(indent=2))
        print("-" * 40)

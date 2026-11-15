import pymupdf
from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extracts all text from a PDF file cleanly."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found at {path}")

    text_chunks = []
    with pymupdf.open(path) as doc:
        for page in doc:
            text_chunks.append(page.get_text("text"))

    return "\n".join(text_chunks).strip()


if __name__ == "__main__":
    sample_dir = Path("data/sample_pdfs")
    for pdf_file in sorted(sample_dir.glob("*.pdf")):
        print(f"--- {pdf_file.name} ---")
        print(extract_text_from_pdf(pdf_file))
        print()

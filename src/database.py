import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from src.parser import RepairOrder
from src.validator import ValidationResult

# Store the SQLite database inside the data/ folder (already ignored by .gitignore)
DB_PATH = Path("data/processed.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)


class Base(DeclarativeBase):
    pass


class RepairOrderRecord(Base):
    __tablename__ = "repair_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ro_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    ro_date: Mapped[str] = mapped_column(String(20), nullable=False)
    vin: Mapped[str] = mapped_column(String(17), nullable=False)
    vehicle: Mapped[str] = mapped_column(String(100), nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    tax: Mapped[float] = mapped_column(Float, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    validation_errors: Mapped[str] = mapped_column(Text, default="[]")
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    items: Mapped[list["LineItemRecord"]] = relationship(
        back_populates="repair_order", cascade="all, delete-orphan"
    )


class LineItemRecord(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repair_order_id: Mapped[int] = mapped_column(ForeignKey("repair_orders.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)

    repair_order: Mapped["RepairOrderRecord"] = relationship(back_populates="items")


def init_db() -> None:
    """Creates the database tables if they do not already exist."""
    Base.metadata.create_all(engine)


def save_repair_order(ro: RepairOrder, validation: ValidationResult) -> tuple[bool, str]:
    """
    Saves a validated repair order and its line items to SQLite.
    Returns (success: bool, message: str). Rejects duplicate RO numbers cleanly.
    """
    init_db()

    with Session(engine) as session:
        existing = session.query(RepairOrderRecord).filter_by(ro_number=ro.ro_number).first()
        if existing:
            return False, f"Duplicate skipped: {ro.ro_number} already exists in the database."

        record = RepairOrderRecord(
            ro_number=ro.ro_number,
            ro_date=ro.date,
            vin=ro.vin,
            vehicle=ro.vehicle,
            subtotal=ro.subtotal,
            tax=ro.tax,
            total=ro.total,
            is_valid=validation.is_valid,
            validation_errors=json.dumps(validation.errors),
            items=[
                LineItemRecord(
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
                for item in ro.items
            ],
        )

        session.add(record)
        session.commit()
        status_label = "VALID" if validation.is_valid else "FLAGGED WITH ERRORS"
        return True, f"Saved {ro.ro_number} ({status_label}) to database."


def get_all_repair_orders() -> list[dict]:
    """Fetches all stored repair orders for display in the dashboard."""
    init_db()
    with Session(engine) as session:
        records = (
            session.query(RepairOrderRecord)
            .order_by(RepairOrderRecord.id.desc())
            .all()
        )
        results = []
        for rec in records:
            results.append(
                {
                    "id": rec.id,
                    "ro_number": rec.ro_number,
                    "date": rec.ro_date,
                    "vin": rec.vin,
                    "vehicle": rec.vehicle,
                    "subtotal": rec.subtotal,
                    "tax": rec.tax,
                    "total": rec.total,
                    "is_valid": rec.is_valid,
                    "errors": json.loads(rec.validation_errors),
                    "item_count": len(rec.items),
                }
            )
        return results

def get_line_items_for_ro(ro_number: str) -> list[dict]:
    """Fetches all line items belonging to a specific repair order number."""
    init_db()
    with Session(engine) as session:
        record = session.query(RepairOrderRecord).filter_by(ro_number=ro_number).first()
        if not record:
            return []
        return [
            {
                "Description": item.description,
                "Qty / Hrs": item.quantity,
                "Unit Price": f"${item.unit_price:.2f}",
                "Line Total": f"${item.line_total:.2f}",
            }
            for item in record.items
        ]

# End-to-end test: process all 4 sample PDFs into SQLite
if __name__ == "__main__":
    from extractor import extract_text_from_pdf
    from parser import parse_repair_order
    from validator import validate_repair_order

    sample_dir = Path("data/sample_pdfs")
    for pdf_file in sorted(sample_dir.glob("*.pdf")):
        raw_text = extract_text_from_pdf(pdf_file)
        parsed_ro = parse_repair_order(raw_text)
        val_result = validate_repair_order(parsed_ro)
        saved, msg = save_repair_order(parsed_ro, val_result)
        print(f"{pdf_file.name}: {msg}")

    print(f"\nTotal records currently in database: {len(get_all_repair_orders())}")

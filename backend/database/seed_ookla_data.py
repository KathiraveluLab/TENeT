"""Seed a compact, real Ookla Open Data sample for local development."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import Base, SessionLocal, engine
from database.models import OoklaPerformance


SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "samples",
    "ookla_performance_sample.csv",
)

FLOAT_FIELDS = (
    "avg_d_kbps",
    "avg_u_kbps",
    "avg_lat_ms",
    "centroid_lat",
    "centroid_lon",
)
INTEGER_FIELDS = ("tests", "devices", "year", "quarter")


def load_sample_rows(sample_path=SAMPLE_PATH):
    """Read and validate the checked-in Ookla sample."""
    with open(sample_path, newline="", encoding="utf-8") as sample_file:
        rows = list(csv.DictReader(sample_file))

    if not rows:
        raise ValueError("Ookla sample is empty")

    parsed = []
    seen_keys = set()
    for line_number, row in enumerate(rows, start=2):
        try:
            item = {field: float(row[field]) for field in FLOAT_FIELDS}
            item.update({field: int(row[field]) for field in INTEGER_FIELDS})
            item["quadkey"] = row["quadkey"].strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Ookla sample row {line_number}: {exc}") from exc

        key = (item["quadkey"], item["year"], item["quarter"])
        if not item["quadkey"] or key in seen_keys:
            raise ValueError(f"Invalid or duplicate Ookla tile at row {line_number}")
        if item["quarter"] not in range(1, 5):
            raise ValueError(f"Invalid Ookla quarter at row {line_number}")
        if item["tests"] < 1 or item["devices"] < 1:
            raise ValueError(f"Invalid Ookla sample counts at row {line_number}")

        seen_keys.add(key)
        parsed.append(item)

    return parsed


def upsert_sample_rows(db, rows):
    """Insert or refresh sample tiles without deleting a full local ingest."""
    for row in rows:
        tile = db.query(OoklaPerformance).filter_by(
            quadkey=row["quadkey"],
            year=row["year"],
            quarter=row["quarter"],
        ).first()
        if tile is None:
            tile = OoklaPerformance(
                quadkey=row["quadkey"],
                year=row["year"],
                quarter=row["quarter"],
            )
            db.add(tile)

        for field in FLOAT_FIELDS + ("tests", "devices"):
            setattr(tile, field, row[field])

    db.commit()
    return len(rows)


def seed_ookla_data():
    """Load the tracked real-data subset into the configured database."""
    Base.metadata.create_all(bind=engine)
    rows = load_sample_rows()
    db = SessionLocal()
    try:
        count = upsert_sample_rows(db, rows)
        print(f"✓ Seeded {count} Ookla Open Data performance tiles")
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_ookla_data()

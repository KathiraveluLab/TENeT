"""
Seed deterministic Ookla-like performance tiles for local development.

Full Ookla ingestion depends on public S3 access and pyarrow. Phase 1 local
setup should still make the performance layer usable, so this seed provides a
small offline sample around Alaska communities.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import SessionLocal, engine, Base
from database.models import OoklaPerformance


SAMPLE_TILES = [
    ("0201000000000001", 61.2181, -149.9003, 92000, 18000, 42, 210, 84),
    ("0201000000000002", 61.5811, -149.4389, 52000, 12000, 58, 90, 38),
    ("0201000000000003", 64.8378, -147.7164, 46000, 9000, 71, 110, 44),
    ("0201000000000004", 60.7922, -161.7558, 18000, 4000, 190, 36, 18),
    ("0201000000000005", 64.5011, -165.4064, 14000, 3000, 230, 28, 14),
    ("0201000000000006", 71.2906, -156.7886, 12000, 2500, 260, 22, 11),
    ("0201000000000007", 58.3019, -134.4197, 78000, 16000, 48, 150, 60),
    ("0201000000000008", 57.0531, -135.3350, 33000, 7000, 88, 43, 20),
    ("0201000000000009", 55.3422, -131.6461, 41000, 8500, 76, 61, 27),
    ("0201000000000010", 51.8800, -176.6581, 8500, 1200, 310, 12, 7),
]


def seed_ookla_sample_data(year: int = 2025, quarter: int = 4):
    """Load a small offline performance dataset."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        deleted = db.query(OoklaPerformance).delete()
        print(f"Cleared {deleted} existing Ookla performance records")

        for idx, (quadkey, lat, lon, down, up, latency, tests, devices) in enumerate(SAMPLE_TILES, start=1):
            db.add(OoklaPerformance(
                quadkey=quadkey,
                tile_x=idx,
                tile_y=idx,
                avg_d_kbps=float(down),
                avg_u_kbps=float(up),
                avg_lat_ms=float(latency),
                tests=int(tests),
                devices=int(devices),
                year=year,
                quarter=quarter,
                centroid_lat=float(lat),
                centroid_lon=float(lon),
            ))

        db.commit()
        print(f"✓ Seeded {len(SAMPLE_TILES)} Ookla performance records for {year} Q{quarter}")
        return len(SAMPLE_TILES)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_ookla_sample_data()

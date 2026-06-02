"""
Ookla Open Data Ingestion Script for Alaska (Optimized)

Uses PyArrow pushdown filtering to efficiently fetch only Alaska tiles
without pre-calculating millions of quadkeys.

Source: s3://ookla-open-data/parquet/performance/type=fixed/

Usage:
    python ingest_ookla.py [--year YEAR] [--quarter QUARTER] [--dry-run]

Example:
    python ingest_ookla.py --year 2024 --quarter 4
"""

import os
import sys
import math
import argparse
from datetime import datetime
from typing import Optional, Tuple

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import pyarrow.parquet as pq
    import pyarrow.dataset as ds
    import pyarrow.compute as pc
    import pandas as pd
except ImportError:
    print("Required packages not installed. Run: pip install pyarrow pandas")
    sys.exit(1)

# ============================================================================
# ALASKA BOUNDING BOX
# ============================================================================
# Using simple bounding box that covers mainland Alaska
# (Aleutian Islands crossing antimeridian handled separately)

AK_MIN_LAT = 51.0
AK_MAX_LAT = 71.5
AK_MIN_LON = -180.0
AK_MAX_LON = -129.0

ZOOM_LEVEL = 16
TILE_SIZE = 256

# ============================================================================
# TILE COORDINATE UTILITIES
# ============================================================================

def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
    """Convert lat/lon to tile X/Y coordinates at given zoom level."""
    lat = max(-85.05112878, min(85.05112878, lat))
    
    n = 2.0 ** zoom
    tile_x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    tile_y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    
    return tile_x, tile_y


def tile_to_lat_lon(tile_x: int, tile_y: int, zoom: int) -> Tuple[float, float]:
    """Get the lat/lon of the tile's center."""
    n = 2.0 ** zoom
    lon = (tile_x + 0.5) / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 0.5) / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def tile_to_quadkey(tile_x: int, tile_y: int, zoom: int) -> str:
    """Convert tile XY coordinates to a quadkey string."""
    quadkey = []
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if (tile_x & mask) != 0:
            digit += 1
        if (tile_y & mask) != 0:
            digit += 2
        quadkey.append(str(digit))
    return ''.join(quadkey)


def quadkey_to_tile(quadkey: str) -> Tuple[int, int, int]:
    """Convert quadkey to tile X, Y, and zoom level."""
    tile_x = 0
    tile_y = 0
    zoom = len(quadkey)
    
    for i, char in enumerate(quadkey):
        bit = zoom - i - 1
        mask = 1 << bit
        digit = int(char)
        
        if digit & 1:  # bit 0 = tile_x
            tile_x |= mask
        if digit & 2:  # bit 1 = tile_y
            tile_y |= mask
    
    return tile_x, tile_y, zoom


def quadkey_to_lat_lon(quadkey: str) -> Tuple[float, float]:
    """
    Convert a quadkey to its tile center lat/lon.
    
    The quadkey encodes the tile position at a given zoom level.
    This is more reliable than using tile_x/tile_y from Ookla data
    which appear to be approximate lon/lat values, not tile coordinates.
    """
    tile_x, tile_y, zoom = quadkey_to_tile(quadkey)
    
    n = 2.0 ** zoom
    lon = (tile_x + 0.5) / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 0.5) / n)))
    lat = math.degrees(lat_rad)
    
    return lat, lon


def get_alaska_tile_bounds(zoom: int = ZOOM_LEVEL) -> dict:
    """
    Calculate the tile X/Y bounds for Alaska at given zoom level.
    Returns min/max tile coordinates for efficient filtering.
    """
    # Southwest corner (min_lat, min_lon)
    sw_tile_x, sw_tile_y = lat_lon_to_tile(AK_MIN_LAT, AK_MIN_LON, zoom)
    
    # Northeast corner (max_lat, max_lon)
    ne_tile_x, ne_tile_y = lat_lon_to_tile(AK_MAX_LAT, AK_MAX_LON, zoom)
    
    # Note: tile_y is inverted (0 at top, increases downward)
    # So min_lat gives larger tile_y, max_lat gives smaller tile_y
    return {
        'min_tile_x': sw_tile_x,
        'max_tile_x': ne_tile_x,
        'min_tile_y': ne_tile_y,  # Smaller y for higher latitude
        'max_tile_y': sw_tile_y,  # Larger y for lower latitude
        'zoom': zoom
    }


# ============================================================================
# OPTIMIZED OOKLA DATA INGESTION
# ============================================================================

def fetch_ookla_data_optimized(
    year: int,
    quarter: int,
    dry_run: bool = False
) -> pd.DataFrame:
    """
    Fetch Ookla performance data for Alaska using PyArrow pushdown filtering.
    
    Uses ANONYMOUS S3 access - no AWS credentials required!
    Ookla Open Data is publicly accessible.
    
    Alaska quadkeys at zoom 16 start with prefixes: 02 (various regions)
    - 0201, 0202: Southern/Central Alaska (Anchorage, Fairbanks area)
    - 0022: Northern Alaska
    - 0032: Eastern Alaska
    - 0212: Southeast Alaska
    
    Args:
        year: Year of data (e.g., 2024)
        quarter: Quarter (1-4)
        dry_run: If True, just print what would be done
    
    Returns:
        DataFrame with Alaska performance data
    """
    from pyarrow import fs
    import pyarrow.compute as pc
    
    # S3 bucket path
    s3_bucket_path = f"ookla-open-data/parquet/performance/type=fixed/year={year}/quarter={quarter}/"
    
    # Alaska quadkey prefixes (zoom level 4, which covers zoom 16 data)
    # These cover all of Alaska including Aleutian Islands
    ALASKA_QUADKEY_PREFIXES = ['0022', '0032', '0201', '0202', '0203', '0210', '0211', '0212']
    
    print(f"\n{'='*60}")
    print(f"OOKLA DATA INGESTION (Anonymous S3 Access)")
    print(f"{'='*60}")
    print(f"Source: s3://{s3_bucket_path}")
    print(f"Alaska quadkey prefixes: {', '.join(ALASKA_QUADKEY_PREFIXES)}")
    
    if dry_run:
        print("\n[DRY RUN] Would fetch data from S3 filtered by quadkey prefixes.")
        return pd.DataFrame()
    
    try:
        print("\nConnecting to S3 (anonymous access)...")
        
        # Create ANONYMOUS S3 filesystem
        s3 = fs.S3FileSystem(region='us-west-2', anonymous=True)
        
        # Create dataset
        print("Loading dataset...")
        dataset = ds.dataset(
            s3_bucket_path,
            filesystem=s3,
            format='parquet'
        )
        
        # Build filter using quadkey prefix matching
        # PyArrow string matching for Alaska quadkeys
        print("Building Alaska quadkey filter...")
        
        # Create combined filter for all Alaska prefixes
        alaska_filter = None
        for prefix in ALASKA_QUADKEY_PREFIXES:
            prefix_filter = pc.starts_with(ds.field('quadkey'), prefix)
            if alaska_filter is None:
                alaska_filter = prefix_filter
            else:
                alaska_filter = alaska_filter | prefix_filter
        
        # Add sanity check: only tiles with actual test data
        valid_data_filter = (
            (ds.field('tests') > 0) &
            (ds.field('avg_d_kbps').is_valid())
        )
        
        combined_filter = alaska_filter & valid_data_filter
        
        # Create scanner with filter
        print("Streaming filtered data from S3 (this may take 1-2 minutes)...")
        scanner = dataset.scanner(
            columns=['quadkey', 'tile_x', 'tile_y', 'avg_d_kbps', 'avg_u_kbps', 
                     'avg_lat_ms', 'tests', 'devices'],
            filter=combined_filter
        )
        
        table = scanner.to_table()
        df = table.to_pandas()
        
        print(f"✓ Loaded {len(df):,} Alaska tiles with valid test data")
        
        if len(df) > 0:
            # Add centroid coordinates - compute from quadkey (NOT tile_x/tile_y which are wrong in Ookla data)
            print("Computing tile centroids from quadkeys...")
            centroids = [
                quadkey_to_lat_lon(row['quadkey'])
                for _, row in df.iterrows()
            ]
            df['centroid_lat'] = [c[0] for c in centroids]
            df['centroid_lon'] = [c[1] for c in centroids]
        
        return df
        
    except Exception as e:
        print(f"\nError fetching from S3: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("  1. Check internet connection")
        print("  2. Verify pyarrow is installed: pip install pyarrow")
        return pd.DataFrame()


def save_to_database(df: pd.DataFrame, year: int, quarter: int):
    """Save Ookla data to the database with sanity checks."""
    if df.empty:
        print("No data to save.")
        return
    
    from database.config import SessionLocal, engine, Base
    from database.models import OoklaPerformance
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Sanity check: verify data quality
        print("\nData Quality Checks:")
        null_speed = df['avg_d_kbps'].isna().sum()
        zero_tests = (df['tests'] == 0).sum()
        print(f"  Tiles with null speed: {null_speed}")
        print(f"  Tiles with zero tests: {zero_tests}")
        
        if null_speed > 0 or zero_tests > 0:
            print("  [INFO] Filtering out invalid tiles...")
            df = df[(df['avg_d_kbps'].notna()) & (df['tests'] > 0)]
            print(f"  Remaining valid tiles: {len(df)}")
        
        # Clear existing data for this period
        existing = db.query(OoklaPerformance).filter(
            OoklaPerformance.year == year,
            OoklaPerformance.quarter == quarter
        ).count()
        
        if existing > 0:
            print(f"\nClearing {existing} existing records for {year} Q{quarter}...")
            db.query(OoklaPerformance).filter(
                OoklaPerformance.year == year,
                OoklaPerformance.quarter == quarter
            ).delete()
            db.commit()
        
        # Insert new data
        print(f"Inserting {len(df)} valid records...")
        records = []
        
        for _, row in df.iterrows():
            record = OoklaPerformance(
                quadkey=row['quadkey'],
                tile_x=int(row['tile_x']),
                tile_y=int(row['tile_y']),
                avg_d_kbps=float(row['avg_d_kbps']),
                avg_u_kbps=float(row['avg_u_kbps']) if pd.notna(row['avg_u_kbps']) else None,
                avg_lat_ms=float(row['avg_lat_ms']) if pd.notna(row['avg_lat_ms']) else None,
                tests=int(row['tests']),
                devices=int(row['devices']) if pd.notna(row['devices']) else None,
                year=year,
                quarter=quarter,
                centroid_lat=float(row['centroid_lat']),
                centroid_lon=float(row['centroid_lon'])
            )
            records.append(record)
        
        db.bulk_save_objects(records)
        db.commit()
        
        print(f"✓ Saved {len(records)} Ookla performance records")
        
        # Print summary
        print(f"\n{'='*40}")
        print(f"DATA SUMMARY")
        print(f"{'='*40}")
        print(f"  Avg Download: {df['avg_d_kbps'].mean()/1000:.1f} Mbps")
        print(f"  Avg Upload:   {df['avg_u_kbps'].mean()/1000:.1f} Mbps")
        print(f"  Avg Latency:  {df['avg_lat_ms'].mean():.1f} ms")
        print(f"  Total Tests:  {df['tests'].sum():,}")
        print(f"  Total Devices: {df['devices'].sum():,}")
        
        # Speed distribution
        print(f"\nSpeed Distribution:")
        excellent = (df['avg_d_kbps'] >= 50000).sum()
        good = ((df['avg_d_kbps'] >= 25000) & (df['avg_d_kbps'] < 50000)).sum()
        moderate = ((df['avg_d_kbps'] >= 10000) & (df['avg_d_kbps'] < 25000)).sum()
        poor = (df['avg_d_kbps'] < 10000).sum()
        print(f"  Excellent (≥50 Mbps): {excellent} ({excellent/len(df)*100:.1f}%)")
        print(f"  Good (25-50 Mbps):    {good} ({good/len(df)*100:.1f}%)")
        print(f"  Moderate (10-25 Mbps): {moderate} ({moderate/len(df)*100:.1f}%)")
        print(f"  Poor (<10 Mbps):      {poor} ({poor/len(df)*100:.1f}%)")
        
    except Exception as e:
        print(f"Error saving to database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# MAIN
# ============================================================================

def get_latest_available_quarter(today: Optional[datetime] = None) -> Tuple[int, int]:
    """
    Determine the latest Ookla quarter likely available on S3.

    Ookla publishes data ~4-6 weeks after each quarter ends:
        Q1 (Jan-Mar) → available ~May
        Q2 (Apr-Jun) → available ~August
        Q3 (Jul-Sep) → available ~November
        Q4 (Oct-Dec) → available ~February

    To stay safe, we always return one full quarter behind the current date.
    Examples (today = Feb 2026  →  Q1 2026  →  returns 2025 Q4)
    """
    now = today or datetime.now()
    current_quarter = (now.month - 1) // 3 + 1
    year = now.year

    quarter = current_quarter - 1
    if quarter == 0:
        quarter = 4
        year -= 1

    return year, quarter


def main():
    auto_year, auto_quarter = get_latest_available_quarter()

    parser = argparse.ArgumentParser(
        description='Ingest Ookla Open Data for Alaska (Optimized)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'Latest auto-detected quarter: {auto_year} Q{auto_quarter}'
    )
    parser.add_argument('--year', type=int, default=auto_year,
                        help=f'Year of data (default: auto-detected → {auto_year})')
    parser.add_argument('--quarter', type=int, default=auto_quarter, choices=[1, 2, 3, 4],
                        help=f'Quarter 1-4 (default: auto-detected → Q{auto_quarter})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without fetching data')
    parser.add_argument('--show-bounds', action='store_true',
                        help='Print Alaska tile bounds and exit')

    args = parser.parse_args()

    print(f"[INFO] Target period: {args.year} Q{args.quarter}")
    if args.year == auto_year and args.quarter == auto_quarter:
        print(f"[INFO] (Auto-detected as latest available quarter based on today's date)")

    if args.show_bounds:
        bounds = get_alaska_tile_bounds(ZOOM_LEVEL)
        print(f"\nAlaska Tile Bounds at Zoom {ZOOM_LEVEL}:")
        print(f"  Tile X: {bounds['min_tile_x']} to {bounds['max_tile_x']}")
        print(f"  Tile Y: {bounds['min_tile_y']} to {bounds['max_tile_y']}")
        print(f"  Theoretical max tiles: {(bounds['max_tile_x']-bounds['min_tile_x']) * (bounds['max_tile_y']-bounds['min_tile_y']):,}")
        print(f"\nNote: Actual tiles will be far fewer (only populated areas with tests)")
        return
    
    # Fetch and save data
    df = fetch_ookla_data_optimized(args.year, args.quarter, args.dry_run)
    
    if not args.dry_run and not df.empty:
        save_to_database(df, args.year, args.quarter)
    
    print("\nDone!")


if __name__ == '__main__':
    main()

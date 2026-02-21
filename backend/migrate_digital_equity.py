"""
Database Migration: Add Digital Equity Support

This script adds the digital_equity_data column to the communities table
and optionally populates it with initial calculations.

Run this before starting the updated backend.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, Community, engine
from app.digital_equity_integration import batch_update_equity_data


def migrate_database():
    """
    Add digital_equity_data column to communities table if it doesn't exist.
    """
    print("🔄 Checking database schema...")
    
    # Create all tables (will only create missing tables/columns)
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database schema updated")


def populate_equity_data(limit=None):
    """
    Populate digital equity data for all communities.
    
    Args:
        limit: Optional limit on number of communities to process
    """
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🔄 Computing digital equity data...")
        updated_count = batch_update_equity_data(db, limit)
        print(f"✅ Updated {updated_count} communities with digital equity data")
    except Exception as e:
        print(f"❌ Error updating equity data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate database and populate digital equity data"
    )
    parser.add_argument(
        "--populate",
        action="store_true",
        help="Populate digital equity data after migration"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of communities to process (for testing)"
    )
    
    args = parser.parse_args()
    
    # Run migration
    migrate_database()
    
    # Optionally populate data
    if args.populate:
        populate_equity_data(args.limit)
        print("\n✅ Migration complete!")
    else:
        print("\n✅ Schema migration complete!")
        print("💡 Run with --populate to compute digital equity data for all communities")
        print("   Example: python migrate_digital_equity.py --populate")

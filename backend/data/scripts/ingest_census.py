#!/usr/bin/env python3
"""
Census ACS Income Data Ingestion Script

Fetches median household income data from US Census Bureau API
for Alaska ZIP Code Tabulation Areas (ZCTAs).

Source: American Community Survey (ACS) 5-Year Estimates
Variable: B19013_001E (Median Household Income)

Usage:
    python ingest_census.py --key YOUR_API_KEY
    
Requirements:
    - Census API key from: https://api.census.gov/data/key_signup.html
"""

import os
import sys
import argparse
import requests
import time
from typing import List, Dict, Optional

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

from database.config import SessionLocal, engine
from database.models import Base, CensusIncome

# Known Alaska ZCTAs (comprehensive list)
# All Alaska ZCTAs are in range 995xx - 999xx
ALASKA_ZCTAS = [
    # Anchorage area
    "99501", "99502", "99503", "99504", "99505", "99506", "99507", "99508",
    "99509", "99510", "99511", "99513", "99514", "99515", "99516", "99517",
    "99518", "99519", "99520", "99521", "99522", "99523", "99524", "99529",
    "99530", "99540",
    # Mat-Su / Eagle River
    "99567", "99577", "99587", "99588",
    # Kenai Peninsula
    "99556", "99568", "99572", "99574", "99575", "99603", "99605", "99610",
    "99611", "99615", "99631", "99635", "99639", "99645", "99654", "99664",
    "99669", "99672",
    # Fairbanks / Interior
    "99701", "99702", "99703", "99704", "99705", "99706", "99707", "99708",
    "99709", "99710", "99711", "99712", "99714", "99716", "99720", "99721",
    "99722", "99723", "99724", "99725", "99726", "99727", "99729", "99730",
    "99732", "99733", "99734", "99736", "99737", "99738", "99739", "99740",
    "99741", "99742", "99743", "99744", "99745", "99746", "99747", "99748",
    "99749", "99750", "99751", "99752", "99753", "99754", "99755", "99756",
    "99757", "99758", "99759", "99760", "99761", "99762", "99763", "99764",
    "99765", "99766", "99767", "99768", "99769", "99770", "99771", "99772",
    "99773", "99774", "99775", "99776", "99777", "99778", "99780", "99781",
    "99782", "99783", "99784", "99785", "99786", "99788", "99789", "99790",
    "99791",
    # Southeast Alaska
    "99801", "99802", "99803", "99811", "99820", "99821", "99824", "99825",
    "99826", "99827", "99829", "99830", "99832", "99833", "99835", "99836",
    "99840", "99841",
    # Ketchikan / Prince of Wales
    "99901", "99903", "99918", "99919", "99921", "99922", "99923", "99925",
    "99926", "99927", "99928", "99929",
    # Western Alaska / Bethel
    "99545", "99546", "99547", "99548", "99549", "99550", "99551", "99552",
    "99553", "99554", "99555", "99557", "99558", "99559", "99561", "99563",
    "99564", "99565", "99566", "99569", "99571", "99573", "99576", "99578",
    "99579", "99580", "99581", "99583", "99585", "99586", "99589", "99590",
    "99591", "99602", "99604", "99606", "99607", "99609", "99612", "99613",
    "99614", "99620", "99621", "99622", "99624", "99625", "99626", "99627",
    "99628", "99630", "99632", "99633", "99634", "99636", "99637", "99638",
    "99640", "99641", "99643", "99644", "99647", "99648", "99649", "99650",
    "99651", "99652", "99653", "99655", "99656", "99657", "99658", "99659",
    "99660", "99661", "99662", "99663", "99665", "99666", "99667", "99668",
    "99670", "99671", "99674", "99675", "99676", "99677", "99678", "99679",
    "99680", "99681", "99682", "99683", "99684", "99685", "99686", "99687",
    "99688", "99689", "99690", "99691", "99692", "99693", "99694", "99695",
]

# ZCTA Centroids for map visualization
ZCTA_CENTROIDS = {
    "99501": (61.2181, -149.9003),
    "99502": (61.1508, -149.9294),
    "99503": (61.1875, -149.8697),
    "99504": (61.2040, -149.7400),
    "99505": (61.2628, -149.6525),
    "99506": (61.2567, -149.8086),
    "99507": (61.1425, -149.8125),
    "99508": (61.2036, -149.8139),
    "99515": (61.1089, -149.8639),
    "99516": (61.0847, -149.7789),
    "99517": (61.1947, -149.9500),
    "99518": (61.1525, -149.9125),
    "99540": (60.9458, -149.1583),
    "99556": (59.6425, -151.5100),
    "99559": (60.7922, -161.7558),
    "99577": (61.2308, -149.4489),
    "99587": (60.9442, -147.4117),
    "99611": (60.5528, -151.2581),
    "99615": (57.7900, -152.4072),
    "99654": (61.5811, -149.4389),
    "99669": (60.5400, -151.2739),
    "99676": (62.3236, -150.1089),
    "99686": (61.1308, -146.3483),
    "99701": (64.8378, -147.7164),
    "99705": (64.8503, -147.8283),
    "99709": (64.8572, -147.8258),
    "99712": (64.9500, -147.4000),
    "99723": (71.2906, -156.7886),
    "99741": (64.5611, -149.0928),
    "99762": (64.5011, -165.4064),
    "99801": (58.3019, -134.4197),
    "99824": (58.3800, -134.6400),
    "99827": (59.4519, -135.9319),
    "99833": (56.8119, -132.9536),
    "99835": (57.0531, -135.3350),
    "99901": (55.3422, -131.6461),
}


def fetch_zcta_batch(zctas: List[str], api_key: str) -> List[Dict]:
    """
    Fetch income data for a batch of ZCTAs.
    """
    url = "https://api.census.gov/data/2022/acs/acs5"
    
    # Join ZCTAs with comma for batch request
    zcta_list = ",".join(zctas)
    
    params = {
        "get": "NAME,B19013_001E",
        "for": f"zip code tabulation area:{zcta_list}",
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        if not data or len(data) < 2:
            return []
        
        headers = data[0]
        records = []
        
        for row in data[1:]:
            record = dict(zip(headers, row))
            income = float(record.get('B19013_001E', 0))
            
            if income > 0:  # Skip missing data
                records.append({
                    'zcta': record.get('zip code tabulation area', ''),
                    'name': record.get('NAME', ''),
                    'median_income': income
                })
        
        return records
        
    except Exception as e:
        print(f"  Error: {e}")
        return []


def fetch_all_alaska_income(api_key: str) -> List[Dict]:
    """
    Fetch income data for all Alaska ZCTAs using batched requests.
    """
    print("📡 Fetching Census ACS 2022 income data for Alaska ZCTAs...")
    
    all_records = []
    batch_size = 50  # Census API can handle multiple ZCTAs per request
    
    # Process in batches
    for i in range(0, len(ALASKA_ZCTAS), batch_size):
        batch = ALASKA_ZCTAS[i:i + batch_size]
        print(f"  Fetching batch {i // batch_size + 1}... ({len(batch)} ZCTAs)")
        
        records = fetch_zcta_batch(batch, api_key)
        all_records.extend(records)
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    print(f"\n✅ Retrieved income data for {len(all_records)} Alaska ZCTAs")
    return all_records


def save_to_database(records: List[Dict], year: int = 2022):
    """
    Save Census income data to the CensusIncome table.
    """
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        saved = 0
        updated = 0
        
        for record in records:
            zcta = str(record['zcta'])
            centroid = ZCTA_CENTROIDS.get(zcta, (None, None))
            
            existing = db.query(CensusIncome).filter_by(zcta=zcta).first()
            
            if existing:
                existing.median_income = record['median_income']
                existing.acs_year = year
                existing.centroid_lat = centroid[0]
                existing.centroid_lon = centroid[1]
                updated += 1
            else:
                census_record = CensusIncome(
                    zcta=zcta,
                    state_fips='02',
                    median_income=record['median_income'],
                    centroid_lat=centroid[0],
                    centroid_lon=centroid[1],
                    acs_year=year
                )
                db.add(census_record)
                saved += 1
        
        db.commit()
        print(f"\n✓ Saved {saved} new, updated {updated} existing records")
        
        # Summary
        total = db.query(CensusIncome).count()
        all_records = db.query(CensusIncome).filter(CensusIncome.median_income.isnot(None)).all()
        avg_income = sum(r.median_income for r in all_records) / len(all_records) if all_records else 0
        
        print(f"\n{'='*50}")
        print(f"CENSUS DATA SUMMARY")
        print(f"{'='*50}")
        print(f"  Total ZCTAs in DB: {total}")
        print(f"  Average Median Income: ${avg_income:,.0f}/year")
        
        # Show income distribution
        low_income = [r for r in all_records if r.median_income < 50000]
        mid_income = [r for r in all_records if 50000 <= r.median_income < 75000]
        high_income = [r for r in all_records if r.median_income >= 75000]
        
        print(f"\n  Income Distribution:")
        print(f"    < $50k:     {len(low_income)} ZCTAs")
        print(f"    $50k-75k:   {len(mid_income)} ZCTAs")
        print(f"    >= $75k:    {len(high_income)} ZCTAs")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch Census income data for Alaska ZCTAs")
    parser.add_argument("--key", required=False, help="Census API Key (overrides CENSUS_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Get API key from environment variable, with command-line override
    api_key = args.key or os.environ.get('CENSUS_API_KEY')
    
    if not api_key:
        print("❌ Error: Census API key required.")
        print("   Set CENSUS_API_KEY environment variable or use --key argument")
        print("   Get a key from: https://api.census.gov/data/key_signup.html")
        sys.exit(1)
    
    print("=" * 60)
    print("CENSUS ACS INCOME DATA INGESTION")
    print("=" * 60)
    
    records = fetch_all_alaska_income(api_key)
    
    if not records:
        print("❌ No data retrieved. Check your API key.")
        sys.exit(1)
    
    # Show sample
    print("\nSample records:")
    for r in records[:5]:
        print(f"  {r['zcta']}: ${r['median_income']:,.0f}/year")
    
    # Save to database
    print("\n📦 Saving to database...")
    save_to_database(records)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

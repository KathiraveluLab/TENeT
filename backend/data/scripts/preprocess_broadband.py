"""
Broadband Data Preprocessing Script for TENeT Project
======================================================
This script cleans and preprocesses the FCC Broadband availability data
to support the "data coverage/confidence" layer for telehealth feasibility.

Input:  ../raw/Broadband_data.csv
Output: ../processed_data/broadband_cleaned.csv
        ../processed_data/broadband_data_gaps.csv

Author: TENeT Project
Date: January 2026
"""

import pandas as pd
import os
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Speed tiers relevant for telehealth (based on FCC/telehealth requirements)
# Minimum for video telehealth: 25 Mbps down / 3 Mbps up
# Good for real-time diagnostics: 100 Mbps down / 20 Mbps up
SPEED_COLS_TO_KEEP = ['speed_25_3', 'speed_100_20']

# Columns to drop (redundant or not useful)
COLS_TO_DROP = [
    'area_data_type',      # Always "Total"
    'geography_type',       # Always "Census Place"
    'geography_desc_full',  # Redundant with geography_desc
    'speed_02_02',          # Too slow for telehealth
    'speed_10_1',           # Too slow for telehealth
    'speed_250_25',         # Overkill for basic telehealth
    'speed_1000_100'        # Overkill for basic telehealth
]

# Technology types to KEEP (most relevant for telehealth feasibility)
TECHNOLOGIES_TO_KEEP = [
    'Any Technology',       # Overall coverage summary
    'All Wired',            # Reliable terrestrial infrastructure
    'NGSO Satellite',       # Low-earth orbit (Starlink, etc.) - viable for telehealth
    'Fiber',                # Best case scenario
    'Cable',                # Common in larger communities
    'All Satellite',        # Fallback option (includes GSO)
]

# Threshold for confidence scoring
LOW_CONFIDENCE_UNITS_THRESHOLD = 50   # Places with < 50 units get LOW confidence
SATELLITE_DEPENDENT_THRESHOLD = 0.9   # If >90% rely on satellite only

# Telehealth minimum speed requirements
TELEHEALTH_MIN_SPEED_COL = 'speed_25_3'  # 25/3 Mbps minimum for video


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_raw_data(filepath: str) -> pd.DataFrame:
    """Load the raw broadband CSV file."""
    print(f"📂 Loading raw data from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"   ✓ Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def drop_unnecessary_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove columns that are redundant or not needed for analysis."""
    cols_to_drop = [col for col in COLS_TO_DROP if col in df.columns]
    df = df.drop(columns=cols_to_drop)
    print(f"🗑️  Dropped {len(cols_to_drop)} unnecessary columns")
    return df


def filter_residential_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only Residential (R) data, drop Business (B).
    Telehealth focus is primarily on residential access.
    """
    original_count = len(df)
    df = df[df['biz_res'] == 'R'].copy()
    df = df.drop(columns=['biz_res'])
    print(f"🏠 Filtered to Residential only: {original_count:,} → {len(df):,} rows")
    return df


def filter_relevant_technologies(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the technology types relevant for telehealth analysis."""
    original_count = len(df)
    df = df[df['technology'].isin(TECHNOLOGIES_TO_KEEP)].copy()
    print(f"📡 Filtered to relevant technologies: {original_count:,} → {len(df):,} rows")
    print(f"   Technologies kept: {df['technology'].unique().tolist()}")
    return df


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns for clarity."""
    rename_map = {
        'geography_id': 'place_id',
        'geography_desc': 'place_name',
        'total_units': 'residential_units',
        'technology': 'tech_type'
    }
    df = df.rename(columns=rename_map)
    print(f"📝 Renamed columns for clarity")
    return df


def add_confidence_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a confidence score based on sample size and data completeness.
    
    Confidence levels:
    - HIGH: Large community (>=50 units) with good data coverage
    - MEDIUM: Moderate size or some data uncertainty
    - LOW: Small community (<50 units) or high data uncertainty
    """
    def calculate_confidence(row):
        units = row['residential_units']
        
        if units < LOW_CONFIDENCE_UNITS_THRESHOLD:
            return 'LOW'
        elif units < 200:
            return 'MEDIUM'
        else:
            return 'HIGH'
    
    df['confidence'] = df.apply(calculate_confidence, axis=1)
    
    # Count by confidence level
    confidence_counts = df.groupby('place_id')['confidence'].first().value_counts()
    print(f"📊 Confidence distribution (by place):")
    for level, count in confidence_counts.items():
        print(f"   {level}: {count} places")
    
    return df


def identify_data_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add flags to identify data gaps and coverage issues.
    
    Flags:
    - SATELLITE_ONLY: No terrestrial (wired) coverage, relies 100% on satellite
    - INTERNET_DESERT: No coverage at telehealth minimum speed (25/3)
    - LOW_TERRESTRIAL: <50% terrestrial coverage at 25/3
    - INFERRED: Data may be modeled/estimated (small sample)
    """
    # We need to pivot to analyze per-place
    # First, let's add flags based on individual tech rows
    
    def flag_row(row):
        flags = []
        tech = row['tech_type']
        speed_25_3 = row.get('speed_25_3', 0)
        
        # Flag specific issues
        if tech == 'Any Technology' and speed_25_3 == 0:
            flags.append('INTERNET_DESERT')
        
        if tech == 'All Wired' and speed_25_3 == 0:
            flags.append('NO_WIRED_25MBPS')
        
        if tech == 'NGSO Satellite' and speed_25_3 > 0.9:
            flags.append('SATELLITE_AVAILABLE')
        
        if row['residential_units'] < LOW_CONFIDENCE_UNITS_THRESHOLD:
            flags.append('SMALL_SAMPLE')
        
        return ';'.join(flags) if flags else ''
    
    df['data_flags'] = df.apply(flag_row, axis=1)
    print(f"🚩 Added data quality flags")
    
    return df


def generate_place_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a summary table with one row per place showing key metrics
    and data gap indicators.
    """
    # Pivot: for each place, get coverage % for key technologies
    summary_rows = []
    
    for place_id in df['place_id'].unique():
        place_data = df[df['place_id'] == place_id]
        place_name = place_data['place_name'].iloc[0]
        units = place_data['residential_units'].iloc[0]
        confidence = place_data['confidence'].iloc[0]
        
        # Get speed coverage for different technologies
        any_tech = place_data[place_data['tech_type'] == 'Any Technology']
        all_wired = place_data[place_data['tech_type'] == 'All Wired']
        ngso_sat = place_data[place_data['tech_type'] == 'NGSO Satellite']
        fiber = place_data[place_data['tech_type'] == 'Fiber']
        
        # Extract coverage percentages
        any_tech_25 = any_tech['speed_25_3'].values[0] if len(any_tech) > 0 else None
        any_tech_100 = any_tech['speed_100_20'].values[0] if len(any_tech) > 0 else None
        wired_25 = all_wired['speed_25_3'].values[0] if len(all_wired) > 0 else None
        ngso_25 = ngso_sat['speed_25_3'].values[0] if len(ngso_sat) > 0 else None
        fiber_25 = fiber['speed_25_3'].values[0] if len(fiber) > 0 else None
        
        # Determine data gaps
        gaps = []
        
        # Internet Desert: No coverage at all at 25/3
        if any_tech_25 is not None and any_tech_25 == 0:
            gaps.append('INTERNET_DESERT')
        
        # Satellite-Only: Has NGSO but no wired at 25/3
        if wired_25 is not None and wired_25 == 0 and ngso_25 is not None and ngso_25 > 0.5:
            gaps.append('SATELLITE_DEPENDENT')
        
        # Low Terrestrial: Wired < 50% at 25/3
        if wired_25 is not None and wired_25 < 0.5 and wired_25 > 0:
            gaps.append('LOW_TERRESTRIAL')
        
        # Low confidence (small sample)
        if confidence == 'LOW':
            gaps.append('LOW_CONFIDENCE')
        
        # Missing data flags
        if any_tech_25 is None:
            gaps.append('MISSING_OVERALL_DATA')
        if wired_25 is None:
            gaps.append('MISSING_WIRED_DATA')
        if ngso_25 is None:
            gaps.append('MISSING_SATELLITE_DATA')
        
        summary_rows.append({
            'place_id': place_id,
            'place_name': place_name,
            'residential_units': units,
            'confidence': confidence,
            'any_tech_25mbps_pct': any_tech_25,
            'any_tech_100mbps_pct': any_tech_100,
            'wired_25mbps_pct': wired_25,
            'ngso_satellite_25mbps_pct': ngso_25,
            'fiber_25mbps_pct': fiber_25,
            'data_gaps': ';'.join(gaps) if gaps else 'NONE',
            'telehealth_viable': 'YES' if (any_tech_25 is not None and any_tech_25 > 0.5) else 'UNCERTAIN' if any_tech_25 is None else 'NO',
            'primary_access': 'WIRED' if (wired_25 is not None and wired_25 > 0.5) else 'SATELLITE' if (ngso_25 is not None and ngso_25 > 0.5) else 'LIMITED'
        })
    
    summary_df = pd.DataFrame(summary_rows)
    print(f"📋 Generated place summary: {len(summary_df)} places")
    
    return summary_df


def print_data_gap_report(summary_df: pd.DataFrame):
    """Print a summary of data gaps for visibility."""
    print("\n" + "="*70)
    print("📊 DATA GAPS SUMMARY REPORT")
    print("="*70)
    
    # Count places by telehealth viability
    viability = summary_df['telehealth_viable'].value_counts()
    print(f"\n🏥 Telehealth Viability:")
    for status, count in viability.items():
        pct = count / len(summary_df) * 100
        print(f"   {status}: {count} places ({pct:.1f}%)")
    
    # Count places by primary access type
    access = summary_df['primary_access'].value_counts()
    print(f"\n📡 Primary Internet Access:")
    for access_type, count in access.items():
        pct = count / len(summary_df) * 100
        print(f"   {access_type}: {count} places ({pct:.1f}%)")
    
    # Count specific data gaps
    print(f"\n⚠️  Data Gap Flags:")
    gap_flags = ['INTERNET_DESERT', 'SATELLITE_DEPENDENT', 'LOW_TERRESTRIAL', 
                 'LOW_CONFIDENCE', 'MISSING_OVERALL_DATA', 'MISSING_WIRED_DATA']
    
    for flag in gap_flags:
        count = summary_df['data_gaps'].str.contains(flag).sum()
        pct = count / len(summary_df) * 100
        print(f"   {flag}: {count} places ({pct:.1f}%)")
    
    # List some example problem places
    print(f"\n🔍 Sample Places with Data Gaps:")
    problem_places = summary_df[summary_df['data_gaps'] != 'NONE'].head(10)
    for _, row in problem_places.iterrows():
        print(f"   • {row['place_name']} ({row['residential_units']} units): {row['data_gaps']}")
    
    print("\n" + "="*70)


def save_outputs(df_cleaned: pd.DataFrame, df_summary: pd.DataFrame, output_dir: str):
    """Save the cleaned data and summary to CSV files."""
    os.makedirs(output_dir, exist_ok=True)
    
    cleaned_path = os.path.join(output_dir, 'broadband_cleaned.csv')
    summary_path = os.path.join(output_dir, 'broadband_data_gaps.csv')
    
    df_cleaned.to_csv(cleaned_path, index=False)
    df_summary.to_csv(summary_path, index=False)
    
    print(f"\n💾 Saved outputs:")
    print(f"   ✓ Cleaned data: {cleaned_path}")
    print(f"   ✓ Data gaps summary: {summary_path}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main preprocessing pipeline."""
    print("\n" + "="*70)
    print("🚀 BROADBAND DATA PREPROCESSING FOR TENeT")
    print("="*70 + "\n")
    
    # Define paths
    script_dir = Path(__file__).parent
    raw_data_path = script_dir.parent / 'raw' / 'Broadband_data.csv'
    output_dir = script_dir.parent / 'processed_data'
    
    # Check if input file exists
    if not raw_data_path.exists():
        print(f"❌ Error: Input file not found at {raw_data_path}")
        return
    
    # Step 1: Load raw data
    df = load_raw_data(str(raw_data_path))
    
    # Step 2: Drop unnecessary columns
    df = drop_unnecessary_columns(df)
    
    # Step 3: Filter to residential data only
    df = filter_residential_only(df)
    
    # Step 4: Filter to relevant technology types
    df = filter_relevant_technologies(df)
    
    # Step 5: Rename columns for clarity
    df = rename_columns(df)
    
    # Step 6: Add confidence scores
    df = add_confidence_score(df)
    
    # Step 7: Add data gap flags
    df = identify_data_gaps(df)
    
    # Step 8: Generate place summary with data gaps
    summary_df = generate_place_summary(df)
    
    # Step 9: Print data gap report
    print_data_gap_report(summary_df)
    
    # Step 10: Save outputs
    save_outputs(df, summary_df, str(output_dir))
    
    print("\n✅ Preprocessing complete!\n")
    
    # Return dataframes for testing/debugging
    return df, summary_df


if __name__ == '__main__':
    main()

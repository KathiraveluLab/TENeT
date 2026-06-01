"""
API routes for Ookla Performance data (Measured Network Performance Layer)
"""
from flask import Blueprint, request, jsonify
from database.config import SessionLocal
from database.models import OoklaPerformance, BroadbandCoverage, CATRegion, CensusIncome
from sqlalchemy import func
import math
import json
import os

performance_bp = Blueprint('performance', __name__, url_prefix='/api/cat')

# Load ISP pricing configuration from external file
def load_isp_config():
    """Load ISP pricing configuration from JSON file."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'isp_pricing.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to defaults if config file not found
        return {
            'isp_pricing': {
                'gci': {'name': 'GCI', 'cost': 125, 'description': 'Major city pricing'},
                'fastwyre': {'name': 'FastWyre/Rural', 'cost': 350, 'description': 'Rural pricing'},
                'starlink': {'name': 'Starlink', 'cost': 120, 'description': 'Satellite'},
                'extreme_rural': {'name': 'Extreme Rural', 'cost': 450, 'description': 'Remote villages'}
            },
            'zcta_mappings': {'gci_urban': [], 'extreme_rural': []},
            'thresholds': {'affordability_burden_pct': 2.0}
        }

# Load config once at startup
ISP_CONFIG = load_isp_config()

# Speed thresholds (kbps)
SPEED_EXCELLENT = 50000   # 50 Mbps
SPEED_GOOD = 25000        # 25 Mbps (telehealth minimum)
SPEED_POOR = 10000        # 10 Mbps
SPEED_CRITICAL = 5000     # 5 Mbps

# Latency thresholds (ms)
LATENCY_GOOD = 50
LATENCY_ACCEPTABLE = 150
LATENCY_POOR = 300


def get_speed_color(speed_kbps: float) -> str:
    """Get color for speed visualization."""
    if speed_kbps is None:
        return '#6b7280'  # Gray - no data
    if speed_kbps >= SPEED_EXCELLENT:
        return '#22c55e'  # Green - excellent
    if speed_kbps >= SPEED_GOOD:
        return '#84cc16'  # Lime - good
    if speed_kbps >= SPEED_POOR:
        return '#eab308'  # Yellow - moderate
    if speed_kbps >= SPEED_CRITICAL:
        return '#f97316'  # Orange - poor
    return '#ef4444'      # Red - critical


def get_speed_label(speed_kbps: float) -> str:
    """Get label for speed."""
    if speed_kbps is None:
        return 'No Data'
    if speed_kbps >= SPEED_EXCELLENT:
        return 'Excellent'
    if speed_kbps >= SPEED_GOOD:
        return 'Good'
    if speed_kbps >= SPEED_POOR:
        return 'Moderate'
    if speed_kbps >= SPEED_CRITICAL:
        return 'Poor'
    return 'Critical'


def reverse_geocode_coords(coords):
    """Best-effort reverse geocoding with a deterministic local fallback."""
    try:
        import reverse_geocoder as rg
        return rg.search(coords)
    except Exception:
        return [{'name': 'Remote Alaska Area', 'admin1': 'Alaska', 'cc': 'US'} for _ in coords]


@performance_bp.route('/performance', methods=['GET'])
def get_performance():
    """
    Get all Ookla performance tiles.
    
    Query params:
        year: Filter by year (default: latest)
        quarter: Filter by quarter (default: latest)
        min_tests: Minimum number of tests (default: 1)
    """
    db = SessionLocal()
    try:
        year = request.args.get('year', type=int)
        quarter = request.args.get('quarter', type=int)
        min_tests = request.args.get('min_tests', type=int, default=1)
        
        query = db.query(OoklaPerformance)
        
        # If no year/quarter specified, get latest
        if not year or not quarter:
            latest = db.query(
                OoklaPerformance.year, 
                OoklaPerformance.quarter
            ).order_by(
                OoklaPerformance.year.desc(),
                OoklaPerformance.quarter.desc()
            ).first()
            
            if latest:
                year, quarter = latest
            else:
                return jsonify({
                    'tiles': [],
                    'count': 0,
                    'message': 'No performance data available'
                }), 200
        
        query = query.filter(
            OoklaPerformance.year == year,
            OoklaPerformance.quarter == quarter
        )
        
        # Filter to Alaska geographic bounds with hardcoded exclusions
        # - North of 60°N: 141st meridian (-141°W) is the border
        # - Panhandle (54-60°N): Only include actual AK coast, exclude BC interior
        #
        # Exclusion coordinates (confirmed Canadian locations):
        # - 59.50°N, 133.50°W (near Atlin, BC)
        # - 60.00°N, 130.50°W (near Watson Lake, YT)
        
        from sqlalchemy import or_, and_, not_
        
        # Hardcoded exclusion zones (Canadian areas that slip through bounds)
        exclusion_zones = [
            # Exclude area around 59-61°N, 130-134°W (BC/Yukon border region)
            and_(
                OoklaPerformance.centroid_lat >= 59.0,
                OoklaPerformance.centroid_lat <= 61.0,
                OoklaPerformance.centroid_lon >= -134.0,
                OoklaPerformance.centroid_lon <= -130.0
            )
        ]
        
        query = query.filter(
            and_(
                or_(
                    # Northern Alaska (above 60°N) - 141st meridian border
                    and_(
                        OoklaPerformance.centroid_lat > 60.0,
                        OoklaPerformance.centroid_lon >= -168.0,
                        OoklaPerformance.centroid_lon <= -141.0
                    ),
                    # Southern Alaska / Panhandle (below 60°N)
                    and_(
                        OoklaPerformance.centroid_lat >= 54.0,
                        OoklaPerformance.centroid_lat <= 60.0,
                        OoklaPerformance.centroid_lon >= -168.0,
                        OoklaPerformance.centroid_lon <= -135.0  # Tightened from -130
                    )
                ),
                # Exclude the hardcoded Canadian zones
                not_(or_(*exclusion_zones))
            )
        )
        
        if min_tests > 1:
            query = query.filter(OoklaPerformance.tests >= min_tests)
        
        tiles = query.all()
        
        result = []
        for tile in tiles:
            speed_mbps = tile.avg_d_kbps / 1000 if tile.avg_d_kbps else None
            
            result.append({
                'quadkey': tile.quadkey,
                'lat': tile.centroid_lat,
                'lon': tile.centroid_lon,
                'avg_d_mbps': round(speed_mbps, 2) if speed_mbps else None,
                'avg_u_mbps': round(tile.avg_u_kbps / 1000, 2) if tile.avg_u_kbps else None,
                'avg_lat_ms': round(tile.avg_lat_ms, 1) if tile.avg_lat_ms else None,
                'tests': tile.tests,
                'devices': tile.devices,
                'color': get_speed_color(tile.avg_d_kbps),
                'label': get_speed_label(tile.avg_d_kbps)
            })
        
        # Calculate summary stats
        speeds = [t.avg_d_kbps for t in tiles if t.avg_d_kbps]
        latencies = [t.avg_lat_ms for t in tiles if t.avg_lat_ms]
        
        summary = {
            'avg_download_mbps': round(sum(speeds) / len(speeds) / 1000, 2) if speeds else None,
            'avg_latency_ms': round(sum(latencies) / len(latencies), 1) if latencies else None,
            'total_tests': sum(t.tests or 0 for t in tiles),
            'total_devices': sum(t.devices or 0 for t in tiles),
            'tiles_excellent': sum(1 for t in tiles if t.avg_d_kbps and t.avg_d_kbps >= SPEED_EXCELLENT),
            'tiles_good': sum(1 for t in tiles if t.avg_d_kbps and SPEED_GOOD <= t.avg_d_kbps < SPEED_EXCELLENT),
            'tiles_poor': sum(1 for t in tiles if t.avg_d_kbps and t.avg_d_kbps < SPEED_POOR)
        }
        
        return jsonify({
            'tiles': result,
            'count': len(result),
            'year': year,
            'quarter': quarter,
            'summary': summary
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@performance_bp.route('/performance/gaps', methods=['GET'])
def get_service_gaps():
    """
    Identify service gaps: regions where FCC claims coverage but Ookla shows poor performance.
    
    A "gap" is where:
    - FCC says 25 Mbps coverage exists (>50% coverage)
    - Ookla measured speeds are <25 Mbps
    
    Includes Reliability Score: Ookla Speed / FCC Claimed Speed
    - Score < 0.2 = Critical Gap (user gets <20% of promised)
    - Score < 0.5 = Major Gap
    - Score < 0.8 = Minor Gap
    """
    db = SessionLocal()
    try:
        # Get FCC broadband data (places with claimed coverage)
        fcc_covered = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.any_tech_25mbps_pct >= 50  # FCC claims >50% have 25 Mbps
        ).all()
        
        # Get Ookla performance data
        ookla_data = db.query(OoklaPerformance).all()
        
        # Build lookup by approximate lat/lon
        ookla_lookup = {}
        for tile in ookla_data:
            if tile.centroid_lat and tile.centroid_lon:
                key = (round(tile.centroid_lat, 1), round(tile.centroid_lon, 1))
                if key not in ookla_lookup:
                    ookla_lookup[key] = []
                ookla_lookup[key].append(tile)
        
        gaps = []
        critical_count = 0
        major_count = 0
        
        # FCC advertises 25 Mbps as the standard (in kbps for comparison)
        FCC_ADVERTISED_SPEED = 25000  # 25 Mbps in kbps
        
        for place in fcc_covered:
            region = None
            if place.region_code:
                region = db.query(CATRegion).filter(
                    CATRegion.region_code == place.region_code
                ).first()
            
            if region and region.centroid_lat and region.centroid_lon:
                key = (round(region.centroid_lat, 1), round(region.centroid_lon, 1))
                nearby_tiles = ookla_lookup.get(key, [])
                
                if nearby_tiles:
                    avg_measured = sum(t.avg_d_kbps or 0 for t in nearby_tiles) / len(nearby_tiles)
                    
                    # Calculate Reliability Score
                    reliability_score = avg_measured / FCC_ADVERTISED_SPEED
                    
                    # Determine gap severity based on reliability
                    if reliability_score < 0.2:
                        gap_severity = 'CRITICAL'
                        gap_color = '#dc2626'  # Red
                        critical_count += 1
                    elif reliability_score < 0.5:
                        gap_severity = 'MAJOR'
                        gap_color = '#f97316'  # Orange
                        major_count += 1
                    elif reliability_score < 0.8:
                        gap_severity = 'MINOR'
                        gap_color = '#eab308'  # Yellow
                    else:
                        continue  # Not a significant gap
                    
                    gaps.append({
                        'place_id': place.place_id,
                        'place_name': place.place_name,
                        'region_code': place.region_code,
                        'lat': region.centroid_lat,
                        'lon': region.centroid_lon,
                        'fcc_claimed_pct': place.any_tech_25mbps_pct,
                        'fcc_advertised_mbps': 25,
                        'ookla_measured_mbps': round(avg_measured / 1000, 2),
                        'reliability_score': round(reliability_score, 2),
                        'gap_severity': gap_severity,
                        'gap_color': gap_color,
                        'sample_size': sum(t.tests or 0 for t in nearby_tiles),
                        'gap_explanation': (
                            f"Users get {reliability_score*100:.0f}% of advertised speed"
                        )
                    })
        
        # Sort by reliability score (worst first)
        gaps.sort(key=lambda x: x['reliability_score'])
        
        return jsonify({
            'gaps': gaps,
            'count': len(gaps),
            'critical_gaps': critical_count,
            'major_gaps': major_count,
            'description': 'Regions where measured speeds are below FCC-claimed 25 Mbps',
            'methodology': {
                'reliability_formula': 'Ookla Speed / FCC Advertised Speed (25 Mbps)',
                'critical_threshold': '< 20% of advertised',
                'major_threshold': '< 50% of advertised',
                'minor_threshold': '< 80% of advertised'
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@performance_bp.route('/performance/by-region/<region_code>', methods=['GET'])
def get_performance_by_region(region_code):
    """
    Get aggregated performance data for a specific CAT region.
    """
    db = SessionLocal()
    try:
        # Get region
        region = db.query(CATRegion).filter(
            CATRegion.region_code == region_code
        ).first()
        
        if not region:
            return jsonify({'error': f'Region {region_code} not found'}), 404
        
        if not region.centroid_lat or not region.centroid_lon:
            return jsonify({
                'region_code': region_code,
                'region_name': region.region_name,
                'message': 'No location data for region'
            }), 200
        
        # Find nearby Ookla tiles (within ~0.5 degrees = ~50km)
        tiles = db.query(OoklaPerformance).filter(
            OoklaPerformance.centroid_lat.between(
                region.centroid_lat - 0.5,
                region.centroid_lat + 0.5
            ),
            OoklaPerformance.centroid_lon.between(
                region.centroid_lon - 0.5,
                region.centroid_lon + 0.5
            )
        ).all()
        
        if not tiles:
            return jsonify({
                'region_code': region_code,
                'region_name': region.region_name,
                'message': 'No Ookla performance data in this region',
                'has_data': False
            }), 200
        
        # Calculate averages
        speeds = [t.avg_d_kbps for t in tiles if t.avg_d_kbps]
        latencies = [t.avg_lat_ms for t in tiles if t.avg_lat_ms]
        
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # Compare with FCC claims
        fcc_data = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.region_code == region_code
        ).first()
        
        fcc_claimed = None
        is_gap = False
        if fcc_data and fcc_data.any_tech_25mbps_pct:
            fcc_claimed = fcc_data.any_tech_25mbps_pct
            is_gap = fcc_claimed >= 50 and avg_speed < SPEED_GOOD
        
        return jsonify({
            'region_code': region_code,
            'region_name': region.region_name,
            'has_data': True,
            'performance': {
                'avg_download_mbps': round(avg_speed / 1000, 2),
                'avg_upload_mbps': round(
                    sum(t.avg_u_kbps or 0 for t in tiles) / len(tiles) / 1000, 2
                ) if tiles else None,
                'avg_latency_ms': round(avg_latency, 1),
                'total_tests': sum(t.tests or 0 for t in tiles),
                'total_devices': sum(t.devices or 0 for t in tiles),
                'tile_count': len(tiles),
                'speed_label': get_speed_label(avg_speed),
                'speed_color': get_speed_color(avg_speed)
            },
            'fcc_comparison': {
                'fcc_claimed_coverage_pct': fcc_claimed,
                'is_service_gap': is_gap,
                'gap_explanation': (
                    f"FCC claims {fcc_claimed:.0f}% have 25 Mbps, but measured avg is {avg_speed/1000:.1f} Mbps"
                    if is_gap else None
                )
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@performance_bp.route('/performance/summary', methods=['GET'])
def get_performance_summary():
    """
    Get overall performance summary for Alaska.
    """
    db = SessionLocal()
    try:
        # Get latest data
        latest = db.query(
            OoklaPerformance.year,
            OoklaPerformance.quarter
        ).order_by(
            OoklaPerformance.year.desc(),
            OoklaPerformance.quarter.desc()
        ).first()
        
        if not latest:
            return jsonify({
                'message': 'No performance data available',
                'has_data': False
            }), 200
        
        year, quarter = latest
        
        tiles = db.query(OoklaPerformance).filter(
            OoklaPerformance.year == year,
            OoklaPerformance.quarter == quarter
        ).all()
        
        speeds = [t.avg_d_kbps for t in tiles if t.avg_d_kbps]
        
        # Speed distribution
        distribution = {
            'excellent': sum(1 for s in speeds if s >= SPEED_EXCELLENT),
            'good': sum(1 for s in speeds if SPEED_GOOD <= s < SPEED_EXCELLENT),
            'moderate': sum(1 for s in speeds if SPEED_POOR <= s < SPEED_GOOD),
            'poor': sum(1 for s in speeds if SPEED_CRITICAL <= s < SPEED_POOR),
            'critical': sum(1 for s in speeds if s < SPEED_CRITICAL)
        }
        
        return jsonify({
            'has_data': True,
            'period': {
                'year': year,
                'quarter': quarter,
                'label': f'Q{quarter} {year}'
            },
            'coverage': {
                'total_tiles': len(tiles),
                'tiles_with_speed_data': len(speeds),
                'total_tests': sum(t.tests or 0 for t in tiles),
                'total_devices': sum(t.devices or 0 for t in tiles)
            },
            'speeds': {
                'avg_download_mbps': round(sum(speeds) / len(speeds) / 1000, 2) if speeds else None,
                'max_download_mbps': round(max(speeds) / 1000, 2) if speeds else None,
                'min_download_mbps': round(min(speeds) / 1000, 2) if speeds else None,
                'median_download_mbps': round(sorted(speeds)[len(speeds)//2] / 1000, 2) if speeds else None
            },
            'distribution': distribution,
            'telehealth_viable_pct': round(
                (distribution['excellent'] + distribution['good']) / len(speeds) * 100, 1
            ) if speeds else 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@performance_bp.route('/performance/top-gaps', methods=['GET'])
def get_top_gaps():
    """
    Get the top priority service gaps with location names for the Gap Hunter panel.
    Returns gaps sorted by priority: low speed + high test count = higher priority.
    
    Query params:
        limit: Number of gaps to return (default: 10)
        min_tests: Minimum test count to consider (default: 5)
    """
    db = SessionLocal()
    try:
        limit = request.args.get('limit', type=int, default=10)
        min_tests = request.args.get('min_tests', type=int, default=5)
        
        # Get latest period
        latest = db.query(
            OoklaPerformance.year, 
            OoklaPerformance.quarter
        ).order_by(
            OoklaPerformance.year.desc(),
            OoklaPerformance.quarter.desc()
        ).first()
        
        if not latest:
            return jsonify({'gaps': [], 'count': 0}), 200
        
        year, quarter = latest
        
        # Query underserved tiles with enough tests to be statistically meaningful
        # Filter out 0.0 Mbps (likely test errors)
        # Note: lat/lon filtering done via geocoding results (centroid data needs fixing)
        gaps = db.query(OoklaPerformance).filter(
            OoklaPerformance.year == year,
            OoklaPerformance.quarter == quarter,
            OoklaPerformance.avg_d_kbps < SPEED_GOOD,  # Below 25 Mbps
            OoklaPerformance.avg_d_kbps > 100,  # Filter out near-zero (likely errors)
            OoklaPerformance.tests >= min_tests
        ).order_by(
            OoklaPerformance.avg_d_kbps.asc()
        ).limit(limit * 5).all()  # Get extra to filter by geocoding
        
        if not gaps:
            return jsonify({'gaps': [], 'count': 0}), 200
        
        # Reverse geocode to get location names
        coords = [(g.centroid_lat, g.centroid_lon) for g in gaps]
        
        locations = reverse_geocode_coords(coords)
        
        result = []
        seen_locations = set()
        
        for i, gap in enumerate(gaps):
            if len(result) >= limit:
                break
            
            location_name = locations[i].get('name', 'Unknown') if i < len(locations) else 'Unknown'
            region = locations[i].get('admin1', '') if i < len(locations) else ''
            country = locations[i].get('cc', '') if i < len(locations) else ''
            
            # Filter: strictly only include Alaska locations
            if region != 'Alaska':
                continue
            
            # Avoid duplicate location names in top list
            loc_key = f"{location_name}_{round(gap.centroid_lat, 1)}"
            if loc_key in seen_locations:
                continue
            seen_locations.add(loc_key)
            
            speed_mbps = gap.avg_d_kbps / 1000
            
            # Determine severity label
            if speed_mbps < 5:
                severity = 'critical'
                severity_label = 'Critical'
            elif speed_mbps < 10:
                severity = 'poor'
                severity_label = 'Poor'
            else:
                severity = 'moderate'
                severity_label = 'Moderate'
            
            result.append({
                'rank': len(result) + 1,
                'name': location_name,
                'region': region,
                'lat': gap.centroid_lat,
                'lon': gap.centroid_lon,
                'quadkey': gap.quadkey,
                'speed_mbps': round(speed_mbps, 1),
                'tests': gap.tests,
                'devices': gap.devices or 0,
                'severity': severity,
                'severity_label': severity_label,
                'color': get_speed_color(gap.avg_d_kbps),
                'gap_from_threshold': round(25 - speed_mbps, 1)
            })
        
        return jsonify({
            'gaps': result,
            'count': len(result),
            'period': f'Q{quarter} {year}',
            'threshold_mbps': 25
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@performance_bp.route('/performance/location', methods=['GET'])
def get_location_name():
    """
    Get location name for given lat/lon coordinates using reverse geocoding.
    Only returns Alaska place names - returns generic name for non-Alaska locations.
    
    Query params:
        lat: Latitude
        lon: Longitude
    """
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        
        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon are required'}), 400
        
        results = reverse_geocode_coords([(lat, lon)])
        
        if results:
            location = results[0]
            region = location.get('admin1', '')
            country = location.get('cc', '')
            
            # Only return the place name if it's in Alaska
            # Otherwise return a generic Alaska location indicator
            if region == 'Alaska' or country == 'US':
                name = location.get('name', 'Alaska')
            else:
                # Non-Alaska location - show generic name
                name = 'Remote Alaska Area'
            
            return jsonify({
                'name': name,
                'region': 'Alaska',  # Always show as Alaska
                'country': 'US',
                'lat': lat,
                'lon': lon
            }), 200
        
        return jsonify({'name': 'Remote Alaska Area', 'region': 'Alaska', 'lat': lat, 'lon': lon}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# AFFORDABILITY ANALYSIS ENDPOINTS
# =============================================================================

# Regional ISP Pricing Model for Alaska - LOADED FROM CONFIG
# Config file: backend/config/isp_pricing.json
#
# GCI - largest ISP, serves major cities (Anchorage, Fairbanks, Juneau)
# FastWyre - smaller provider, serves Interior Alaska rural areas  
# Starlink - satellite, available everywhere but requires hardware investment
#
# EXTREME INEQUITY EXAMPLE: Fort Yukon pays $450/mo for capped internet
# while Anchorage pays $125/mo for unlimited

# Get pricing and ZCTA mappings from config
GCI_SERVED_ZCTAS = set(ISP_CONFIG.get('zcta_mappings', {}).get('gci_urban', []))
EXTREME_RURAL_ZCTAS = set(ISP_CONFIG.get('zcta_mappings', {}).get('extreme_rural', []))
ISP_PRICING = ISP_CONFIG.get('isp_pricing', {})
AFFORDABLE_THRESHOLD_PCT = ISP_CONFIG.get('thresholds', {}).get('affordability_burden_pct', 2.0)


def get_regional_internet_cost(zcta: str) -> tuple:
    """
    Get the realistic internet cost for a ZCTA based on regional ISP availability.
    Reads pricing from config/isp_pricing.json.
    
    Returns: (cost, isp_name, description)
    """
    if zcta in EXTREME_RURAL_ZCTAS:
        pricing = ISP_PRICING.get('extreme_rural', {'cost': 450, 'name': 'Extreme Rural', 'description': 'Remote'})
        return (pricing['cost'], pricing['name'], pricing['description'])
    elif zcta in GCI_SERVED_ZCTAS:
        pricing = ISP_PRICING.get('gci', {'cost': 125, 'name': 'GCI', 'description': 'Urban'})
        return (pricing['cost'], pricing['name'], pricing['description'])
    else:
        # Rural areas not served by GCI - use FastWyre/rural pricing
        pricing = ISP_PRICING.get('fastwyre', {'cost': 350, 'name': 'FastWyre', 'description': 'Rural'})
        return (pricing['cost'], pricing['name'], pricing['description'])


@performance_bp.route('/performance/affordability', methods=['GET'])
def get_affordability():
    """
    Get internet affordability analysis by ZCTA using REGIONAL ISP PRICING.
    
    Uses realistic pricing based on available ISPs:
    - GCI (major cities): $125/month unlimited
    - FastWyre/Rural (Interior Alaska): $350/month capped
    - Extreme Rural (remote villages): $450/month capped
    
    Returns areas where internet is economically inaccessible (cost > 2% of income).
    
    Query params:
        use_regional: Use regional ISP pricing (default: true)
        monthly_cost: Override cost for all areas (optional)
        threshold: Affordability threshold as % of income (default: 2.0)
    """
    db = SessionLocal()
    try:
        use_regional = request.args.get('use_regional', type=str, default='true').lower() == 'true'
        override_cost = request.args.get('monthly_cost', type=float)
        threshold = request.args.get('threshold', type=float, default=AFFORDABLE_THRESHOLD_PCT)
        
        # Fetch all Census income records
        income_data = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0
        ).all()
        
        if not income_data:
            return jsonify({
                'error': 'No Census income data available. Run ingest_census.py first.',
                'zones': [],
                'count': 0
            }), 200
        
        result = []
        affordable_count = 0
        unaffordable_count = 0
        
        for record in income_data:
            # Get regional pricing or use override
            if override_cost:
                monthly_cost = override_cost
                isp_name = 'Custom'
                isp_description = f'User-specified ${override_cost}/mo'
            elif use_regional:
                monthly_cost, isp_name, isp_description = get_regional_internet_cost(record.zcta)
            else:
                monthly_cost = 120  # Starlink default
                isp_name = 'Starlink'
                isp_description = 'Default satellite pricing'
            
            monthly_income = record.median_income / 12
            burden_pct = (monthly_cost / monthly_income) * 100 if monthly_income > 0 else 100
            is_affordable = burden_pct < threshold
            
            if is_affordable:
                affordable_count += 1
                status = 'AFFORDABLE'
                color = '#22c55e'  # Green
            else:
                unaffordable_count += 1
                status = 'UNAFFORDABLE'
                color = '#ef4444'  # Red
            
            result.append({
                'zcta': record.zcta,
                'lat': record.centroid_lat,
                'lon': record.centroid_lon,
                'median_income': record.median_income,
                'monthly_income': round(monthly_income, 2),
                'internet_cost': monthly_cost,
                'isp': isp_name,
                'isp_description': isp_description,
                'burden_pct': round(burden_pct, 2),
                'status': status,
                'is_affordable': is_affordable,
                'color': color,
                'population': record.population,
                'households': record.total_households
            })
        
        # Sort by burden (most burdened first)
        result.sort(key=lambda x: x['burden_pct'], reverse=True)
        
        return jsonify({
            'zones': result,
            'count': len(result),
            'monthly_cost': monthly_cost,
            'threshold_pct': threshold,
            'summary': {
                'affordable': affordable_count,
                'unaffordable': unaffordable_count,
                'affordable_pct': round(affordable_count / len(result) * 100, 1) if result else 0
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@performance_bp.route('/performance/affordability/combined', methods=['GET'])
def get_combined_analysis():
    """
    Combine speed data with affordability analysis.
    
    Shows areas that have:
    - Good speed BUT unaffordable = "Coverage without Access"
    - Good speed AND affordable = "True Access"
    - Poor speed = "Infrastructure Gap"
    
    Query params:
        monthly_cost: Internet cost per month (default: $120)
    """
    db = SessionLocal()
    try:
        monthly_cost = request.args.get('monthly_cost', type=float, default=ISP_PRICING.get('starlink', {}).get('cost', 120))
        
        # Get latest performance data by ZCTA area
        # This joins performance tiles with census income data by proximity
        
        # First get Census data
        income_data = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.centroid_lat.isnot(None)
        ).all()
        
        if not income_data:
            return jsonify({
                'error': 'No Census income data. Run ingest_census.py first.',
                'combined': []
            }), 200
        
        # Get performance summary by geographic area
        # For simplicity, we'll aggregate performance data near each ZCTA centroid
        
        result = []
        
        for census in income_data:
            if not census.centroid_lat or not census.centroid_lon:
                continue
            
            # Find performance tiles near this ZCTA (within ~10km)
            lat_range = 0.1  # ~11km
            lon_range = 0.2  # ~11km at Alaska latitudes
            
            nearby_tiles = db.query(OoklaPerformance).filter(
                OoklaPerformance.centroid_lat.between(
                    census.centroid_lat - lat_range,
                    census.centroid_lat + lat_range
                ),
                OoklaPerformance.centroid_lon.between(
                    census.centroid_lon - lon_range,
                    census.centroid_lon + lon_range
                )
            ).all()
            
            # Calculate average speed in area
            if nearby_tiles:
                avg_speed_kbps = sum(t.avg_d_kbps or 0 for t in nearby_tiles) / len(nearby_tiles)
                avg_speed_mbps = avg_speed_kbps / 1000
                has_coverage = avg_speed_mbps >= 25  # Meets telehealth threshold
                total_tests = sum(t.tests or 0 for t in nearby_tiles)
            else:
                avg_speed_mbps = 0
                has_coverage = False
                total_tests = 0
            
            # Calculate affordability
            monthly_income = census.median_income / 12 if census.median_income else 0
            burden_pct = (monthly_cost / monthly_income) * 100 if monthly_income > 0 else 100
            is_affordable = burden_pct < AFFORDABLE_THRESHOLD_PCT
            
            # Determine combined status
            if has_coverage and is_affordable:
                status = 'TRUE_ACCESS'
                status_label = 'True Access'
                color = '#22c55e'  # Green
            elif has_coverage and not is_affordable:
                status = 'COVERAGE_NO_ACCESS'
                status_label = 'Coverage Without Access'
                color = '#f59e0b'  # Orange - has infrastructure but can't afford
            else:
                status = 'INFRASTRUCTURE_GAP'
                status_label = 'Infrastructure Gap'
                color = '#ef4444'  # Red
            
            result.append({
                'zcta': census.zcta,
                'lat': census.centroid_lat,
                'lon': census.centroid_lon,
                'avg_speed_mbps': round(avg_speed_mbps, 1),
                'has_coverage': has_coverage,
                'median_income': census.median_income,
                'monthly_income': round(monthly_income, 2),
                'burden_pct': round(burden_pct, 2),
                'is_affordable': is_affordable,
                'status': status,
                'status_label': status_label,
                'color': color,
                'population': census.population,
                'tests': total_tests
            })
        
        # Summary
        true_access = sum(1 for r in result if r['status'] == 'TRUE_ACCESS')
        coverage_no_access = sum(1 for r in result if r['status'] == 'COVERAGE_NO_ACCESS')
        infra_gap = sum(1 for r in result if r['status'] == 'INFRASTRUCTURE_GAP')
        
        return jsonify({
            'combined': result,
            'count': len(result),
            'monthly_cost': monthly_cost,
            'summary': {
                'true_access': true_access,
                'coverage_without_access': coverage_no_access,
                'infrastructure_gap': infra_gap,
                'true_access_pct': round(true_access / len(result) * 100, 1) if result else 0
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

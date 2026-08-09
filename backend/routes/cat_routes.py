"""
API routes for Community Access Tier (CAT) data management
"""
from database.models import CATRegion, CATDataPoint, HealthcareSite, CensusIncome, BroadbandCoverage
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import math
import json
from database.config import SessionLocal
from database.handlers import CATDataHandler
from services.data_importer import CATDataImporter
from services.healthcare_desert_calculator import HealthcareDesertCalculator, haversine_km as _haversine_km
from services.isp_config import ISP_CONFIG as _ISP_CONFIG, get_internet_cost as _get_regional_internet_cost
from services.research_profile_service import ResearchProfileService
from services.telehealth_classification import TelehealthClassificationService
from services.season_constants import (
    SEASON_SUMMER, SEASON_WINTER, SEASON_YEAR_ROUND, VALID_SEASONS, 
    ROAD_QUALITY_LOCAL, VALID_ROAD_QUALITIES,
    get_season_display_name
)

cat_bp = Blueprint('cat', __name__, url_prefix='/api/cat')

# Priority classification thresholds
HIGH_NECESSITY_THRESHOLD = 70
MODERATE_NECESSITY_THRESHOLD = 50
HIGH_CONNECTIVITY_THRESHOLD = 60
LOW_CONNECTIVITY_THRESHOLD = 40

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'geojson', 'json'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _to_float_or_none(value):
    return float(value) if value is not None else None


def _normalize_filter_value(value):
    return str(value or '').strip().lower()


def _region_group(region):
    properties = region.properties or {}
    return (
        properties.get('region')
        or properties.get('economic_region')
        or properties.get('area')
        or 'unknown'
    )


def _broadband_for_regions(db, region_codes):
    if not region_codes:
        return {}

    records = db.query(BroadbandCoverage).filter(
        BroadbandCoverage.region_code.in_(region_codes)
    ).all()

    lookup = {}
    for record in records:
        if record.region_code and record.region_code not in lookup:
            lookup[record.region_code] = record
    return lookup


def _has_broadband_data_gap(record):
    if record is None:
        return True
    return bool((record.data_gaps or '').strip())


def _data_confidence(record):
    if record is None:
        return 'missing'
    return (record.confidence or 'unknown').lower()


def _build_telehealth_context(db, regions):
    contexts = TelehealthClassificationService.classify_regions(db, regions)
    return {
        code: {
            'telehealth_status': context.classification.status,
            'affordability_status': context.classification.affordability_status,
        }
        for code, context in contexts.items()
    }


def _build_desert_score_lookup(db, regions):
    region_codes = [region.region_code for region in regions if region.region_code]
    if not region_codes:
        return {}

    data_points = db.query(CATDataPoint).filter(
        CATDataPoint.region_code.in_(region_codes)
    ).all()
    points_by_region = {}
    for point in data_points:
        points_by_region.setdefault(point.region_code, []).append(point)

    sites = db.query(HealthcareSite).all()
    active_sites = [
        site for site in sites
        if site.is_active and site.latitude is not None and site.longitude is not None
    ]

    sites_by_region = {}
    specialist_regions = set()
    for site in sites:
        if not site.region_code:
            continue
        sites_by_region[site.region_code] = sites_by_region.get(site.region_code, 0) + 1
        if site.has_specialists:
            specialist_regions.add(site.region_code)

    score_lookup = {}
    clinic_types = {'clinic', 'health_center', 'community_health_center'}

    for region in regions:
        if region.centroid_lat is None or region.centroid_lon is None:
            score_lookup[region.region_code] = None
            continue

        region_points = points_by_region.get(region.region_code, [])
        if region_points:
            center_lat = sum(point.latitude for point in region_points) / len(region_points)
            center_lon = sum(point.longitude for point in region_points) / len(region_points)
            travel_time = region_points[0].travel_time_minutes
        else:
            center_lat = region.centroid_lat
            center_lon = region.centroid_lon
            travel_time = None

        if active_sites:
            clinic_dist = float('inf')
            hospital_dist = float('inf')

            for site in active_sites:
                distance = _haversine_km(center_lat, center_lon, site.latitude, site.longitude)

                site_type = (site.site_type or '').lower()
                if site_type in clinic_types:
                    clinic_dist = min(clinic_dist, distance)
                if site_type == 'hospital':
                    hospital_dist = min(hospital_dist, distance)

            clinic_dist = 999 if clinic_dist == float('inf') else clinic_dist
            hospital_dist = 999 if hospital_dist == float('inf') else hospital_dist
        else:
            clinic_dist = 999
            hospital_dist = 999

        clinic_score = HealthcareDesertCalculator.score_distance_component(clinic_dist)
        hospital_score = min(100.0, (hospital_dist / 500.0) * 100.0)
        distance_score = (0.6 * hospital_score) + (0.4 * clinic_score)
        density_score = HealthcareDesertCalculator.score_density_component(
            sites_by_region.get(region.region_code, 0)
        )
        specialist_score = HealthcareDesertCalculator.score_specialist_component(
            region.region_code in specialist_regions
        )
        transport_score = HealthcareDesertCalculator.score_transport_component(
            travel_time,
            transport_mode='road',
        )

        score_lookup[region.region_code] = round(float(
            0.50 * distance_score +
            0.15 * density_score +
            0.15 * specialist_score +
            0.20 * transport_score
        ), 2)

    return score_lookup


def _build_region_summary(db, regions):
    broadband_lookup = _broadband_for_regions(
        db,
        [region.region_code for region in regions if region.region_code]
    )
    telehealth_lookup = _build_telehealth_context(db, regions)
    desert_score_lookup = _build_desert_score_lookup(db, regions)

    summaries = []
    for region in regions:
        broadband = broadband_lookup.get(region.region_code)
        telehealth = telehealth_lookup.get(region.region_code, {})
        summaries.append({
            'id': region.id,
            'region_code': region.region_code,
            'name': region.region_name,
            'lat': _to_float_or_none(region.centroid_lat),
            'lon': _to_float_or_none(region.centroid_lon),
            'cat_tier': region.tier_level if region.tier_level is not None else None,
            'telehealth_status': telehealth.get('telehealth_status', 'DATA_UNAVAILABLE'),
            'desert_score': desert_score_lookup.get(region.region_code),
            'affordability_status': telehealth.get('affordability_status', 'unknown'),
            'data_confidence': _data_confidence(broadband),
            'has_data_gap': _has_broadband_data_gap(broadband),
            'region': _region_group(region),
        })

    return summaries


def _parse_bool_filter(value):
    normalized = _normalize_filter_value(value)
    if normalized in {'true', '1', 'yes', 'missing', 'gap', 'gaps'}:
        return True
    if normalized in {'false', '0', 'no', 'complete', 'available'}:
        return False
    return None


def _parse_desert_expression(value):
    text = str(value or '').strip()
    if not text:
        return None

    operator = None
    if text[:2] in {'>=', '<='}:
        operator = text[:2]
        text = text[2:].strip()
    elif text[:1] in {'>', '<'}:
        operator = text[:1]
        text = text[1:].strip()

    try:
        score = float(text)
    except ValueError:
        return None

    return operator or 'range', score


def _parse_region_search_args(args):
    filters = {
        'name': args.get('name') or '',
        'tier': args.get('tier'),
        'status': args.get('status'),
        'desert_min': args.get('desert_min'),
        'desert_max': args.get('desert_max'),
        'data_gap': args.get('data_gap'),
        'region': args.get('region'),
    }

    plain_terms = []
    q = args.get('q') or ''
    for token in q.split():
        key, separator, value = token.partition(':')
        key = key.lower()

        if separator and key == 'tier':
            filters['tier'] = value
        elif separator and key == 'status':
            filters['status'] = value
        elif separator and key == 'data':
            filters['data_gap'] = value
        elif separator and key == 'desert':
            parsed = _parse_desert_expression(value)
            if parsed:
                operator, score = parsed
                if operator in {'>', '>='}:
                    filters['desert_min'] = score
                elif operator in {'<', '<='}:
                    filters['desert_max'] = score
        elif separator and key == 'region':
            filters['region'] = value
        else:
            plain_terms.append(token)

    if plain_terms:
        filters['name'] = ' '.join(
            term for term in [filters['name'], ' '.join(plain_terms)]
            if term
        )

    return filters


def _matches_status_filter(value, status_filter):
    if not status_filter:
        return True

    normalized_status = _normalize_filter_value(value).replace('_', '')
    normalized_filter = _normalize_filter_value(status_filter).replace('_', '')
    allowed = {
        'telehealthready',
        'communityanchor',
        'criticalgap',
        'critical',
        'dataunavailable',
        'missing',
        'unknown',
    }
    if normalized_filter not in allowed:
        return True

    return normalized_filter in normalized_status or normalized_status in normalized_filter


def _filter_region_summaries(summaries, filters):
    filtered = list(summaries)

    name_filter = _normalize_filter_value(filters.get('name'))
    if name_filter:
        filtered = [
            item for item in filtered
            if name_filter in _normalize_filter_value(item.get('name'))
            or name_filter in _normalize_filter_value(item.get('region_code'))
        ]

    try:
        tier_filter = int(filters.get('tier')) if filters.get('tier') not in (None, '') else None
    except (TypeError, ValueError):
        tier_filter = None
    if tier_filter in {1, 2, 3, 4}:
        filtered = [item for item in filtered if item.get('cat_tier') == tier_filter]

    status_filter = filters.get('status')
    filtered = [
        item for item in filtered
        if _matches_status_filter(item.get('telehealth_status'), status_filter)
    ]

    try:
        desert_min = float(filters.get('desert_min')) if filters.get('desert_min') not in (None, '') else None
    except (TypeError, ValueError):
        desert_min = None
    if desert_min is not None:
        filtered = [
            item for item in filtered
            if item.get('desert_score') is not None and item.get('desert_score') >= desert_min
        ]

    try:
        desert_max = float(filters.get('desert_max')) if filters.get('desert_max') not in (None, '') else None
    except (TypeError, ValueError):
        desert_max = None
    if desert_max is not None:
        filtered = [
            item for item in filtered
            if item.get('desert_score') is not None and item.get('desert_score') <= desert_max
        ]

    data_gap_filter = _parse_bool_filter(filters.get('data_gap'))
    if data_gap_filter is not None:
        filtered = [
            item for item in filtered
            if item.get('has_data_gap') is data_gap_filter
        ]

    region_filter = _normalize_filter_value(filters.get('region'))
    if region_filter:
        filtered = [
            item for item in filtered
            if region_filter in _normalize_filter_value(item.get('region'))
        ]

    return filtered


# Region endpoints
@cat_bp.route('/regions', methods=['GET'])
def get_regions():
    """
    Get all regions with optional season adjustment.
    
    Query params:
        tier: Filter by base tier level
        season: 'summer', 'winter', or 'year_round' (adjusts tier levels)
    """
    db = SessionLocal()
    try:
        tier_level = request.args.get('tier', type=int)
        season = request.args.get('season', SEASON_YEAR_ROUND)
        
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND

        if tier_level:
            regions = CATDataHandler.get_regions_by_tier(db, tier_level)
        else:
            regions = db.query(CATRegion).all()

        result = []
        for region in regions:
            base_tier = region.tier_level
            base_score = region.access_score or 50
            
            # Calculate season-adjusted tier and score
            adjusted_tier, adjusted_score, explanation = _calculate_seasonal_tier(
                base_tier, base_score, region.properties, season
            )
            
            # Calculate healthcare necessity score
            necessity_data = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
                db, region.region_code, season
            )
            necessity_score = necessity_data['necessity_score'] if necessity_data else 0
            
            result.append({
                'id': region.id,
                'region_name': region.region_name,
                'region_code': region.region_code,
                'tier_level': adjusted_tier,  # Season-adjusted tier
                'base_tier': base_tier,  # Original tier for reference
                'population': region.population,
                'area_sqkm': region.area_sqkm,
                'access_score': adjusted_score,  # Season-adjusted score
                'base_access_score': base_score,
                'necessity_score': necessity_score,
                'centroid_lat': float(region.centroid_lat) if region.centroid_lat else None,
                'centroid_lon': float(region.centroid_lon) if region.centroid_lon else None,
                'description': explanation,  # Season-adjusted explanation
                'season': season,
                'created_at': region.created_at.isoformat() if region.created_at else None
            })

        return jsonify({
            'regions': result, 
            'total': len(result),
            'season': season,
            'season_display': get_season_display_name(season)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        db.close()


@cat_bp.route('/regions/summary', methods=['GET'])
def get_regions_summary():
    """
    Return lightweight community records for sidebar lists.

    This endpoint intentionally excludes geometry, GeoJSON, and popup detail
    payloads so the frontend can populate navigation without downloading map
    boundaries.
    """
    db = SessionLocal()
    try:
        regions = db.query(CATRegion).order_by(CATRegion.region_name).all()
        summaries = _build_region_summary(db, regions)

        return jsonify({
            'regions': summaries,
            'count': len(summaries)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        db.close()


@cat_bp.route('/regions/<region_code>/research-profile', methods=['GET'])
def get_research_profile(region_code):
    """Return the shared research profile for one community."""
    db = SessionLocal()
    try:
        profile = ResearchProfileService.get_profile(
            db,
            region_code,
            request.args.get('season', SEASON_YEAR_ROUND),
        )
        if profile is None:
            return jsonify({
                'error': 'Community not found',
                'region_code': region_code,
            }), 404

        return jsonify(profile), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        db.close()


@cat_bp.route('/regions/research-profiles', methods=['GET'])
def get_research_profiles():
    """Return shared research profiles for 2-3 pinned communities."""
    raw_codes = request.args.get('codes', '')
    codes = []
    for code in raw_codes.split(','):
        normalized = code.strip()
        if normalized and normalized not in codes:
            codes.append(normalized)

    if not codes:
        return jsonify({
            'error': 'codes query parameter is required',
            'profiles': [],
            'count': 0,
            'missing_codes': [],
        }), 400

    db = SessionLocal()
    try:
        profiles, missing_codes = ResearchProfileService.get_profiles(
            db,
            codes[:3],
            request.args.get('season', SEASON_YEAR_ROUND),
        )
        return jsonify({
            'profiles': profiles,
            'count': len(profiles),
            'missing_codes': missing_codes,
            'season': ResearchProfileService.normalize_season(
                request.args.get('season', SEASON_YEAR_ROUND)
            ),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        db.close()


@cat_bp.route('/regions/search', methods=['GET'])
def search_regions():
    """
    Search lightweight community summaries for sidebar discovery.

    Supports query params:
        q/name, tier, status, desert_min, desert_max, data_gap, region

    q also accepts compact filters like:
        tier:4 status:critical desert:>70 data:missing Bethel
    """
    db = SessionLocal()
    try:
        filters = _parse_region_search_args(request.args)
        regions = db.query(CATRegion).order_by(CATRegion.region_name).all()
        summaries = _build_region_summary(db, regions)
        filtered = _filter_region_summaries(summaries, filters)

        return jsonify({
            'regions': filtered,
            'count': len(filtered),
            'filters': filters
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        db.close()


def _calculate_seasonal_tier(base_tier: int, base_score: float, properties: dict, season: str):
    """
    Calculate season-adjusted CAT tier and access score.
    
    Winter: Reduces access (tiers can go up: worse)
    Summer: Maintains or improves access (tiers can go down: better)
    Year-round: Uses base values
    
    Returns: (adjusted_tier, adjusted_score, explanation)
    """
    # Get original justification
    base_explanation = ''
    if properties:
        base_explanation = properties.get('tier_justification', '')
    
    if season == SEASON_YEAR_ROUND:
        return base_tier, base_score, base_explanation
    
    # Check access modes from properties
    primary_modes = []
    if properties:
        modes_str = properties.get('primary_access_modes', '')
        primary_modes = [m.strip() for m in modes_str.split(',') if m.strip()]
    
    has_road = 'road' in primary_modes
    has_air = 'air' in primary_modes
    has_water = 'water' in primary_modes
    
    if season == SEASON_WINTER:
        # Winter restricts seasonal transport
        tier_penalty = 0
        score_penalty = 0
        restricted_modes = []
        
        # Water is mostly unavailable in winter
        if has_water and not has_air:
            score_penalty += 25
            restricted_modes.append('water (frozen)')
        elif has_water:
            score_penalty += 10
            restricted_modes.append('water (limited)')
        
        # Seasonal roads are harder, and if water freezes and they have no air, they rely solely on roads (Tier 3 max)
        if has_road:
            score_penalty += 5  # Roads harder but not impossible
            if not has_air:
                tier_penalty = max(tier_penalty, 3 - base_tier)
        
        # If a community has no road and no air, they are completely isolated in winter (water freezes)
        elif not has_air:
            tier_penalty = max(tier_penalty, 4 - base_tier)
            
        # No air = significant penalty for all tiers
        if not has_air:
            score_penalty += 20
        
        adjusted_tier = min(4, int(base_tier) + int(tier_penalty))
        adjusted_score = max(0.0, float(base_score) - float(score_penalty))
        
        if tier_penalty > 0:
            explanation = f"Winter access: {', '.join(restricted_modes) if restricted_modes else 'Limited transport'}"
        else:
            explanation = f"Winter access: Air available; {base_explanation}"
        
        return adjusted_tier, float(f"{adjusted_score:.1f}"), explanation
    
    elif season == SEASON_SUMMER:
        # Summer can improve access slightly for communities with seasonal routes
        tier_bonus = 0
        score_bonus = 0
        
        # Multi-modal access in summer
        if has_water and has_air:
            score_bonus += 10
        
        if has_road and has_water:
            score_bonus += 5
        
        # Tier 4 with some access can become Tier 3 in summer
        if base_tier == 4 and (has_water or has_air):
            tier_bonus = -1
        
        adjusted_tier = max(1, int(base_tier) + int(tier_bonus))
        adjusted_score = min(100.0, float(base_score) + float(score_bonus))
        
        if tier_bonus < 0:
            explanation = f"Summer access: Seasonal routes available; improved from Tier {base_tier}"
        elif score_bonus > 0:
            explanation = f"Summer access: All modes available; {base_explanation}"
        else:
            explanation = base_explanation
        
        return adjusted_tier, float(f"{adjusted_score:.1f}"), explanation
    
    return base_tier, base_score, base_explanation




@cat_bp.route('/regions/<region_code>', methods=['GET'])
def get_region(region_code):
    """Get specific region by code"""
    db = SessionLocal()
    try:
        region = CATDataHandler.get_region_by_code(db, region_code)
        
        if not region:
            return jsonify({'error': f'Region not found: {region_code}'}), 404
        
        result = {
            'id': region.id,
            'region_name': region.region_name,
            'region_code': region.region_code,
            'tier_level': region.tier_level,
            'population': region.population,
            'area_sqkm': region.area_sqkm,
            'access_score': region.access_score,
            'centroid_lat': region.centroid_lat,
            'centroid_lon': region.centroid_lon,
            'description': region.properties.get('tier_justification', '') if region.properties else '',
            'created_at': region.created_at.isoformat() if region.created_at else None
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        db.close()


# Data points endpoints
@cat_bp.route('/data-points', methods=['GET'])
def get_data_points():
    """Get data points with optional filters"""
    try:
        region_code = request.args.get('region_code')
        access_type = request.args.get('access_type')
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius_km = request.args.get('radius_km', type=float, default=10)
        
        db = SessionLocal()
        
        if lat and lon:
            data_points = CATDataHandler.get_data_points_in_radius(db, lat, lon, radius_km)
        elif region_code:
            data_points = CATDataHandler.get_data_points_by_region(db, region_code, access_type)
        else:
            from database.models import CATDataPoint
            data_points = db.query(CATDataPoint).limit(100).all()
        
        result = []
        for point in data_points:
            result.append({
                'id': point.id,
                'region_code': point.region_code,
                'latitude': point.latitude,
                'longitude': point.longitude,
                'location_name': point.location_name,
                'access_type': point.access_type,
                'access_quality': point.access_quality,
                'distance_km': point.distance_km,
                'travel_time_minutes': point.travel_time_minutes,
                'is_active': point.is_active,
                'verified': point.verified
            })
        
        db.close()
        return jsonify({'data_points': result, 'count': len(result)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Upload endpoints
@cat_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload CSV or GeoJSON file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: csv, geojson, json'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit('.', 1)[1].lower()
        if file_type == 'json':
            file_type = 'geojson'
        
        # Create upload record
        db = SessionLocal()
        upload_data = {
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'status': 'pending'
        }
        upload = CATDataHandler.create_upload_record(db, upload_data)
        
        # Process file
        if file_type == 'csv':
            count, message = CATDataImporter.import_csv(db, file_path, upload.id)
        elif file_type == 'geojson':
            count, message = CATDataImporter.import_geojson(db, file_path, upload.id)
        else:
            db.close()
            return jsonify({'error': 'Unsupported file type'}), 400
        
        db.close()
        
        return jsonify({
            'message': message,
            'upload_id': upload.id,
            'records_processed': count
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Gating logic endpoints
@cat_bp.route('/gating/check', methods=['POST'])
def check_gating():
    """Check if a data point passes gating rules"""
    try:
        data = request.json
        point_id = data.get('point_id')
        tier_level = data.get('tier_level')
        
        if not point_id or not tier_level:
            return jsonify({'error': 'point_id and tier_level are required'}), 400
        
        db = SessionLocal()
        from database.models import CATDataPoint
        data_point = db.query(CATDataPoint).filter(CATDataPoint.id == point_id).first()
        
        if not data_point:
            db.close()
            return jsonify({'error': 'Data point not found'}), 404
        
        result = CATDataHandler.check_access_gating(db, data_point, tier_level)
        db.close()
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cat_bp.route('/gating/rules', methods=['GET'])
def get_gating_rules():
    """Get all active gating rules"""
    try:
        tier_level = request.args.get('tier', type=int)
        db = SessionLocal()
        
        rules = CATDataHandler.get_active_gating_rules(db, tier_level)
        
        result = []
        for rule in rules:
            result.append({
                'id': rule.id,
                'rule_name': rule.rule_name,
                'tier_level': rule.tier_level,
                'min_access_score': rule.min_access_score,
                'max_distance_km': rule.max_distance_km,
                'max_travel_time': rule.max_travel_time,
                'access_types': rule.access_types,
                'is_active': rule.is_active,
                'priority': rule.priority
            })
        
        db.close()
        return jsonify({'rules': result, 'count': len(result)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cat_bp.route('/gating/rules', methods=['POST'])
def create_gating_rule():
    """Create a new gating rule"""
    try:
        data = request.json
        db = SessionLocal()
        
        rule = CATDataHandler.create_gating_rule(db, data)
        
        result = {
            'id': rule.id,
            'rule_name': rule.rule_name,
            'tier_level': rule.tier_level,
            'created_at': rule.created_at.isoformat() if rule.created_at else None
        }
        
        db.close()
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Statistics endpoint
@cat_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get database statistics"""
    try:
        db = SessionLocal()
        stats = CATDataHandler.get_statistics(db)
        db.close()
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# GeoJSON Boundaries API (Choropleth Layer)
# =============================================================================

# Path to Alaska boundaries GeoJSON
BOUNDARIES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    'data', 'raw', 'Alaska_Borough_and_Census_Area_Boundaries.geojson'
)

@cat_bp.route('/boundaries', methods=['GET'])
def get_boundaries():
    """
    Serve Alaska Borough and Census Area boundary polygons.
    
    Returns GeoJSON FeatureCollection with properties:
    - CommunityName: Borough/Census Area name
    - EconomicRegion: Economic region grouping
    - FIPS: Census FIPS code
    - Census_Area: 'Y' if census area, null if borough
    """
    try:
        if not os.path.exists(BOUNDARIES_FILE):
            return jsonify({
                'error': 'Boundaries file not found',
                'path': BOUNDARIES_FILE
            }), 404
        
        with open(BOUNDARIES_FILE, 'r') as f:
            geojson = json.load(f)
        
        return jsonify(geojson), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cat_bp.route('/boundaries/summary', methods=['GET'])
def get_boundaries_summary():
    """
    Get a summary of all regions without full geometry (for dropdowns, lists).
    """
    try:
        if not os.path.exists(BOUNDARIES_FILE):
            return jsonify({'error': 'Boundaries file not found'}), 404
        
        with open(BOUNDARIES_FILE, 'r') as f:
            geojson = json.load(f)
        
        regions = []
        for feature in geojson.get('features', []):
            props = feature.get('properties', {})
            regions.append({
                'name': props.get('CommunityName'),
                'fips': props.get('FIPS'),
                'economic_region': props.get('EconomicRegion'),
                'is_census_area': props.get('Census_Area') == 'Y'
            })
        
        return jsonify({
            'regions': regions,
            'count': len(regions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Feasibility Evaluation API (PR-3)
# =============================================================================

@cat_bp.route('/feasibility/<region_code>', methods=['GET'])
def evaluate_feasibility(region_code):
    """
    Evaluate telehealth feasibility for a region.
    
    This is the authoritative domain-level API for feasibility decisions.
    
    Query params:
        telehealth_mode: Optional - 'video', 'audio', 'store_forward' (CAT-4 only)
    
    Returns:
        Structured feasibility decision with explanation suitable for
        map visualization and policy interpretation.
    """
    db = SessionLocal()
    try:
        # Get telehealth mode (only applies to CAT-4)
        telehealth_mode = request.args.get('telehealth_mode')
        
        # Look up the region
        region = CATDataHandler.get_region_by_code(db, region_code)
        if not region:
            return jsonify({
                'error': f"Region '{region_code}' not found",
                'decision': 'ERROR'
            }), 404
        
        # Get representative data point for this region
        from database.models import CATDataPoint
        data_point = db.query(CATDataPoint).filter(
            CATDataPoint.region_code == region_code,
            CATDataPoint.is_active == True
        ).order_by(CATDataPoint.timestamp.desc()).first()
        
        # Build base response
        response = {
            'region_code': region.region_code,
            'region_name': region.region_name,
            'cat_tier': region.tier_level,
            'telehealth_mode': telehealth_mode or 'all',
            'metrics_used': {}
        }
        
        # No data point available
        if not data_point:
            response.update({
                'feasible': False,
                'decision': 'INSUFFICIENT_DATA',
                'failed_gate': None,
                'explanation': 'No connectivity data available for this region'
            })
            return jsonify(response), 200
        
        # Add metrics to response
        response['metrics_used'] = {
            'bandwidth_mbps': data_point.throughput_mbps,
            'latency_ms': data_point.latency_ms,
            'access_score': data_point.access_quality
        }
        
        # Apply tier-appropriate gating logic
        if region.tier_level == 4:
            # CAT-4: Use mode-aware telehealth feasibility
            result = CATDataHandler.check_cat4_telehealth_feasibility(
                data_point, telehealth_mode
            )
            
            response['feasible'] = result['feasible']
            response['decision'] = 'FEASIBLE' if result['feasible'] else 'NOT_FEASIBLE'
            response['mode_results'] = result['mode_results']
            
            if not result['feasible'] and result['failure_reasons']:
                expl_str = str(result['failure_reasons'][0])
                response['explanation'] = expl_str
                # Determine failed gate from explanation
                explanation = expl_str.lower()
                if 'bandwidth' in explanation:
                    response['failed_gate'] = 'BANDWIDTH'
                elif 'latency' in explanation:
                    response['failed_gate'] = 'LATENCY'
                elif 'access score' in explanation:
                    response['failed_gate'] = 'ACCESS_SCORE'
                else:
                    response['failed_gate'] = 'UNKNOWN'
            else:
                response['failed_gate'] = None
                response['explanation'] = 'Telehealth is feasible for this region'
        else:
            # CAT-1/2/3: Use standard gating logic
            result = CATDataHandler.check_access_gating(db, data_point, region.tier_level)
            
            response['feasible'] = result['allowed']
            response['decision'] = 'FEASIBLE' if result['allowed'] else 'NOT_FEASIBLE'
            
            if not result['allowed'] and result['failed_rules']:
                first_failure = result['failed_rules'][0]
                response['failed_gate'] = first_failure['rule']
                response['explanation'] = first_failure['reasons'][0] if first_failure['reasons'] else 'Gating rule failed'
            else:
                response['failed_gate'] = None
                response['explanation'] = 'All gating rules passed'
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'decision': 'ERROR'}), 500
    finally:
        db.close()


# =============================================================================
# Healthcare Sites & Desert Score API
# =============================================================================

@cat_bp.route('/healthcare-sites', methods=['GET'])
def get_healthcare_sites():
    """Get all healthcare sites, optionally filtered by region"""
    db = SessionLocal()
    try:
        region_code = request.args.get('region_code')
        site_type = request.args.get('site_type')
        
        query = db.query(HealthcareSite)
        
        if region_code:
            query = query.filter(HealthcareSite.region_code == region_code)
        if site_type:
            query = query.filter(HealthcareSite.site_type == site_type)
        
        sites = query.all()
        
        result = [{
            'id': site.id,
            'name': site.name,
            'site_type': site.site_type,
            'latitude': site.latitude,
            'longitude': site.longitude,
            'region_code': site.region_code,
            'has_emergency': site.has_emergency,
            'has_specialists': site.has_specialists,
            'services': site.services,
            'address': site.address
        } for site in sites]
        
        return jsonify({'sites': result, 'count': len(result)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/healthcare-sites', methods=['POST'])
def create_healthcare_site():
    """Create a new healthcare site"""
    db = SessionLocal()
    try:
        data = request.json
        
        if not data.get('name') or not data.get('latitude') or not data.get('longitude'):
            return jsonify({'error': 'name, latitude, and longitude are required'}), 400
        
        site = HealthcareSite(
            name=data['name'],
            site_type=data.get('site_type', 'clinic'),
            latitude=data['latitude'],
            longitude=data['longitude'],
            region_code=data.get('region_code'),
            has_emergency=data.get('has_emergency', False),
            has_specialists=data.get('has_specialists', False),
            services=data.get('services'),
            address=data.get('address')
        )
        
        db.add(site)
        db.commit()
        
        return jsonify({
            'id': site.id,
            'message': 'Healthcare site created'
        }), 201
        
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/healthcare-necessity/<region_code>', methods=['GET'])
def get_healthcare_necessity(region_code):
    """
    Get healthcare necessity score for a region.
    Higher score = greater need for telehealth (0-100).
    
    Query params:
        season: 'summer', 'winter', or 'year_round' (default: year_round)
        road_quality: 'highway', 'local', or 'seasonal' (default: local)
    """
    db = SessionLocal()
    try:
        # Get season from query params (user-selected)
        season = request.args.get('season', SEASON_YEAR_ROUND)
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND
        
        road_quality = request.args.get('road_quality', ROAD_QUALITY_LOCAL)
        if road_quality not in VALID_ROAD_QUALITIES:
            road_quality = ROAD_QUALITY_LOCAL
        
        result = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
            db, region_code, season, road_quality
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/healthcare-necessity', methods=['GET'])
def get_all_healthcare_necessity():
    """
    Get necessity scores for all regions, sorted by score (highest first).
    
    Query params:
        season: 'summer', 'winter', or 'year_round' (default: year_round)
        road_quality: 'highway', 'local', or 'seasonal' (default: local)
    """
    db = SessionLocal()
    try:
        season = request.args.get('season', SEASON_YEAR_ROUND)
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND
        
        road_quality = request.args.get('road_quality', ROAD_QUALITY_LOCAL)
        if road_quality not in VALID_ROAD_QUALITIES:
            road_quality = ROAD_QUALITY_LOCAL
        
        results = HealthcareDesertCalculator.get_all_region_scores(db, season, road_quality)
        
        return jsonify({
            'regions': results,
            'count': len(results),
            'season_applied': season,
            'season_display': get_season_display_name(season)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/telehealth-priority/<region_code>', methods=['GET'])
def get_telehealth_priority(region_code):
    """
    Calculate telehealth deployment priority by combining:
    - Healthcare necessity (desert score) - season-adjusted
    - Internet feasibility (CAT tier score)
    
    Query params:
        season: 'summer', 'winter', or 'year_round' (default: year_round)
        road_quality: 'highway', 'local', or 'seasonal' (default: local)
    
    Returns priority classification: HIGH, CRITICAL, MODERATE, LOW
    """
    db = SessionLocal()
    try:
        # Get season from query params (user-selected)
        season = request.args.get('season', SEASON_YEAR_ROUND)
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND
        
        road_quality = request.args.get('road_quality', ROAD_QUALITY_LOCAL)
        if road_quality not in VALID_ROAD_QUALITIES:
            road_quality = ROAD_QUALITY_LOCAL
        
        # Get region
        region = CATDataHandler.get_region_by_code(db, region_code)
        if not region:
            return jsonify({'error': f'Region {region_code} not found'}), 404
        
        # 1. Calculate healthcare necessity (season-adjusted)
        necessity = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
            db, region_code, season, road_quality
        )
        necessity_score = necessity['necessity_score']
        
        # 2. Get internet feasibility
        from database.models import CATDataPoint, BroadbandCoverage
        data_point = db.query(CATDataPoint).filter(
            CATDataPoint.region_code == region_code,
            CATDataPoint.is_active == True
        ).first()

        # Also fetch FCC broadband coverage for this region
        broadband = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.region_code == region_code
        ).first()

        if broadband and broadband.wired_25mbps_pct is not None and broadband.wired_25mbps_pct >= 0:
            # Prefer wired connectivity percentage to avoid 100% satellite false-positives in remote areas
            connectivity_score = round(broadband.wired_25mbps_pct * 100)
        elif broadband and broadband.any_tech_25mbps_pct is not None and broadband.primary_access != 'SATELLITE_DEPENDENT':
            connectivity_score = round(broadband.any_tech_25mbps_pct * 100)
        elif data_point and data_point.throughput_mbps is not None:
            # Scale throughput mbps to a score (0 to 100) assuming 100 Mbps is an ideal connection
            connectivity_score = min(100, round((data_point.throughput_mbps / 100.0) * 100))
        elif broadband and broadband.any_tech_25mbps_pct is not None:
            # Fallback to any_tech but severely penalize if satellite dependent
            connectivity_score = round((broadband.any_tech_25mbps_pct * 100) / 2)
        else:
            connectivity_score = 0
        
        # 3. Determine priority classification with season-contextual recommendations
        season_display = get_season_display_name(season)
        
        # Season-specific context for recommendations
        if season == SEASON_WINTER:
            season_context = "Winter conditions limit transport options. "
            transport_note = "Seasonal roads/water frozen."
        elif season == SEASON_SUMMER:
            season_context = "Summer provides optimal access. "
            transport_note = "All transport modes available."
        else:
            season_context = "Year-round average conditions. "
            transport_note = "Conservative transport assumptions."
        
        if necessity_score > HIGH_NECESSITY_THRESHOLD:
            if connectivity_score > HIGH_CONNECTIVITY_THRESHOLD:
                priority = 'HIGH'
                color = '#22c55e'  # Green
                label = f'Telehealth Recommended ({season_display})'
                recommendation = f'{season_context}High need + capable infrastructure. Deploy telehealth immediately.'
            elif connectivity_score < LOW_CONNECTIVITY_THRESHOLD:
                priority = 'CRITICAL'
                color = '#ef4444'  # Red
                label = f'Infrastructure Gap ({season_display})'
                recommendation = f'{season_context}Critical need but insufficient connectivity. {transport_note} Prioritize infrastructure investment.'
            else:  # Moderate connectivity (40-60)
                priority = 'MODERATE'
                color = '#f97316'  # Orange
                label = f'Mixed Priority ({season_display})'
                recommendation = f'{season_context}High need with moderate connectivity. Consider store-and-forward telehealth.'
                
        elif necessity_score > MODERATE_NECESSITY_THRESHOLD:
            if connectivity_score > HIGH_CONNECTIVITY_THRESHOLD:
                priority = 'MODERATE'
                color = '#eab308'  # Yellow
                label = f'Consider Telehealth ({season_display})'
                recommendation = f'{season_context}Moderate need with good connectivity. Good candidate for pilot programs.'
            else:
                priority = 'LOW'
                color = '#3b82f6'  # Blue
                label = f'Lower Priority ({season_display})'
                recommendation = f'{season_context}Moderate need with limited connectivity. {transport_note}'
                
        else:
            priority = 'LOW'
            color = '#3b82f6'  # Blue
            label = f'Adequate Access ({season_display})'
            recommendation = f'{season_context}In-person care is accessible. Telehealth not priority.'
        
        response = {
            'region_code': region_code,
            'region_name': region.region_name,
            'cat_tier': region.tier_level,
            
            # Scores
            'necessity_score': necessity_score,
            'connectivity_score': connectivity_score,
            'combined_priority': round((necessity_score * connectivity_score) / 100, 2),
            
            # Classification
            'priority': priority,
            'color': color,
            'label': label,
            'recommendation': recommendation,
            
            # Season context (explicit)
            'season_scenario': {
                'active_season': season,
                'season_display': get_season_display_name(season),
                'road_quality': road_quality,
                'assumption': 'User-selected seasonal scenario for planning. '
                             'Transport difficulty is adjusted based on season.'
            },
            
            # Details
            'healthcare_details': necessity,
            'connectivity_details': {
                'bandwidth_mbps': data_point.throughput_mbps if data_point else None,
                'latency_ms': data_point.latency_ms if data_point else None,
                'feasible_for_video': connectivity_score > 60,
                'coverage_25mbps_pct': round(broadband.any_tech_25mbps_pct * 100) if broadband and broadband.any_tech_25mbps_pct is not None else None,
                'primary_access': broadband.primary_access if broadband else None,
                'data_source': 'ookla' if (data_point and data_point.throughput_mbps is not None) else ('fcc' if (broadband and broadband.any_tech_25mbps_pct is not None) else None)
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


# =============================================================================
# Broadband Coverage & Data Gaps API (Data Coverage Layer)
# =============================================================================

@cat_bp.route('/broadband', methods=['GET'])
def get_broadband_coverage():
    """
    Get broadband coverage data with data gap indicators.
    
    Query params:
        confidence: Filter by confidence level (HIGH, MEDIUM, LOW)
        telehealth_viable: Filter by viability (YES, NO, UNCERTAIN)
        primary_access: Filter by access type (WIRED, SATELLITE, LIMITED)
        has_gaps: If 'true', return only places with data gaps
    
    Returns:
        List of broadband coverage records with data quality flags
    """
    from database.models import BroadbandCoverage
    
    db = SessionLocal()
    try:
        query = db.query(BroadbandCoverage)
        
        # Apply filters
        confidence = request.args.get('confidence')
        if confidence:
            query = query.filter(BroadbandCoverage.confidence == confidence.upper())
        
        telehealth_viable = request.args.get('telehealth_viable')
        if telehealth_viable:
            query = query.filter(BroadbandCoverage.telehealth_viable == telehealth_viable.upper())
        
        primary_access = request.args.get('primary_access')
        if primary_access:
            query = query.filter(BroadbandCoverage.primary_access == primary_access.upper())
        
        has_gaps = request.args.get('has_gaps')
        if has_gaps and has_gaps.lower() == 'true':
            query = query.filter(BroadbandCoverage.data_gaps.isnot(None))
        
        # Order by place name
        records = query.order_by(BroadbandCoverage.place_name).all()
        
        result = []
        for r in records:
            result.append({
                'place_id': r.place_id,
                'place_name': r.place_name,
                'residential_units': r.residential_units,
                'coverage': {
                    'any_tech_25mbps_pct': r.any_tech_25mbps_pct,
                    'any_tech_100mbps_pct': r.any_tech_100mbps_pct,
                    'wired_25mbps_pct': r.wired_25mbps_pct,
                    'ngso_satellite_25mbps_pct': r.ngso_satellite_25mbps_pct,
                    'fiber_25mbps_pct': r.fiber_25mbps_pct
                },
                'confidence': r.confidence,
                'data_gaps': r.data_gaps.split(';') if r.data_gaps else [],
                'telehealth_viable': r.telehealth_viable,
                'primary_access': r.primary_access,
                'region_code': r.region_code,
                'data_source': r.data_source
            })
        
        # Summary statistics
        total = len(result)
        by_confidence = {
            'HIGH': sum(1 for r in result if r['confidence'] == 'HIGH'),
            'MEDIUM': sum(1 for r in result if r['confidence'] == 'MEDIUM'),
            'LOW': sum(1 for r in result if r['confidence'] == 'LOW')
        }
        with_gaps = sum(1 for r in result if r['data_gaps'])
        
        return jsonify({
            'broadband': result,
            'count': total,
            'summary': {
                'by_confidence': by_confidence,
                'satellite_dependent': sum(1 for r in result if 'SATELLITE_DEPENDENT' in r['data_gaps']),
                'with_data_gaps': with_gaps,
                'low_confidence': by_confidence['LOW']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/broadband/<place_id>', methods=['GET'])
def get_broadband_by_place(place_id):
    """Get broadband coverage for a specific place by ID."""
    from database.models import BroadbandCoverage
    
    db = SessionLocal()
    try:
        record = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.place_id == place_id
        ).first()
        
        if not record:
            return jsonify({'error': f'Place not found: {place_id}'}), 404
        
        return jsonify({
            'place_id': record.place_id,
            'place_name': record.place_name,
            'residential_units': record.residential_units,
            'coverage': {
                'any_tech_25mbps_pct': record.any_tech_25mbps_pct,
                'any_tech_100mbps_pct': record.any_tech_100mbps_pct,
                'wired_25mbps_pct': record.wired_25mbps_pct,
                'ngso_satellite_25mbps_pct': record.ngso_satellite_25mbps_pct,
                'fiber_25mbps_pct': record.fiber_25mbps_pct
            },
            'confidence': record.confidence,
            'data_gaps': record.data_gaps.split(';') if record.data_gaps else [],
            'telehealth_viable': record.telehealth_viable,
            'primary_access': record.primary_access,
            'region_code': record.region_code,
            'data_source': record.data_source
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/data-gaps', methods=['GET'])
def get_data_gaps_summary():
    """
    Get a summary of all data gaps across the system.
    
    Returns counts and lists of places with specific data quality issues,
    supporting the 'data coverage/confidence' layer visualization.
    """
    from database.models import BroadbandCoverage
    
    db = SessionLocal()
    try:
        all_records = db.query(BroadbandCoverage).all()
        
        # Aggregate gap statistics
        gap_stats = {
            'SATELLITE_DEPENDENT': [],
            'LOW_TERRESTRIAL': [],
            'LOW_CONFIDENCE': [],
            'INTERNET_DESERT': [],
            'MISSING_WIRED_DATA': [],
            'MISSING_SATELLITE_DATA': []
        }
        
        for r in all_records:
            if r.data_gaps:
                gaps = r.data_gaps.split(';')
                for gap in gaps:
                    gap = gap.strip()
                    lst = gap_stats.get(gap)
                    if isinstance(lst, list):
                        lst.append({
                            'place_id': r.place_id,
                            'place_name': r.place_name,
                            'confidence': r.confidence
                        })
        
        # Build response
        summary = {
            'total_places': len(all_records),
            'places_with_gaps': sum(1 for r in all_records if r.data_gaps),
            'gap_breakdown': {}
        }
        
        for gap_type, places in gap_stats.items():
            pct = len(places) / max(1, len(all_records)) * 100.0 if all_records else 0.0
            bd = summary['gap_breakdown']
            if isinstance(bd, dict):
                bd[gap_type] = {
                    'count': len(places),
                    'percentage': round(float(pct), 1),  # type: ignore
                    'places': list(places)[:10]  # type: ignore
                }
        
        # Confidence distribution
        summary['confidence_distribution'] = {
            'HIGH': sum(1 for r in all_records if r.confidence == 'HIGH'),
            'MEDIUM': sum(1 for r in all_records if r.confidence == 'MEDIUM'),
            'LOW': sum(1 for r in all_records if r.confidence == 'LOW')
        }
        
        # Telehealth viability
        summary['telehealth_viability'] = {
            'YES': sum(1 for r in all_records if r.telehealth_viable == 'YES'),
            'NO': sum(1 for r in all_records if r.telehealth_viable == 'NO'),
            'UNCERTAIN': sum(1 for r in all_records if r.telehealth_viable == 'UNCERTAIN')
        }
        
        # Primary access type
        summary['primary_access'] = {
            'WIRED': sum(1 for r in all_records if r.primary_access == 'WIRED'),
            'SATELLITE': sum(1 for r in all_records if r.primary_access == 'SATELLITE'),
            'LIMITED': sum(1 for r in all_records if r.primary_access == 'LIMITED')
        }
        
        return jsonify(summary), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


# =============================================================================
# AFFORDABILITY & SAFETY NET ENDPOINTS
# =============================================================================

@cat_bp.route('/regions/<region_code>/affordability', methods=['GET'])
def get_region_affordability(region_code):
    """
    Get affordability analysis for a specific region.
    
    Uses ZCTA income data with fallback to nearest ZCTA if exact match not found.
    """
    db = SessionLocal()
    try:
        region = CATDataHandler.get_region_by_code(db, region_code)
        if not region or not region.centroid_lat:
            return jsonify({'error': 'Region not found'}), 404
        
        # Find nearest ZCTA with income data
        lat_range = 0.5  # ~55km
        lon_range = 1.0  # ~55km at high latitudes
        
        candidates = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.between(region.centroid_lat - lat_range, region.centroid_lat + lat_range),
            CensusIncome.centroid_lon.between(region.centroid_lon - lon_range, region.centroid_lon + lon_range)
        ).all()
        
        # Find closest ZCTA
        best = None
        min_dist = float('inf')
        
        for c in candidates:
            if c.centroid_lat and c.centroid_lon:
                dist = _haversine_km(region.centroid_lat, region.centroid_lon, c.centroid_lat, c.centroid_lon)
                if dist < min_dist:
                    min_dist = dist
                    best = c
        
        if best is None:
            # No income data found - return unavailable status
            return jsonify({
                'has_income_data': False,
                'income_source': 'unavailable',
                'message': 'No Census income data available for this region',
                'region_code': region_code,
                'region_name': region.region_name
            }), 200
        
        # Calculate affordability
        assert best is not None
        zcta_str = str(best.zcta) if hasattr(best, 'zcta') and best.zcta else ""
        cost, isp_name = _get_regional_internet_cost(zcta_str)
        med_inc = float(getattr(best, 'median_income', 0) or 0)
        monthly_income = med_inc / 12.0
        burden_pct = float((cost / monthly_income) * 100.0) if monthly_income > 0 else 100.0
        
        t_conf = _ISP_CONFIG.get('thresholds', {})
        t_val = t_conf.get('affordability_burden_pct', 2.0) if isinstance(t_conf, dict) else 2.0
        threshold = float(t_val) if isinstance(t_val, (int, float)) else 2.0
        
        is_affordable = bool(burden_pct < threshold)
        
        return jsonify({
            'has_income_data': True,
            'income_source': 'ZCTA',
            'zcta': zcta_str,
            'distance_km': float(f"{min_dist:.1f}"),
            'median_income': med_inc,
            'monthly_income': float(f"{monthly_income:.2f}"),
            'internet_cost': float(cost),
            'isp': str(isp_name),
            'burden_pct': float(f"{burden_pct:.2f}"),
            'threshold_pct': threshold,
            'is_affordable': is_affordable,
            'status': 'AFFORDABLE' if is_affordable else 'UNAFFORDABLE',
            'region_code': region_code,
            'region_name': region.region_name
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/regions/<region_code>/safety-net', methods=['GET'])
def get_region_safety_net(region_code):
    """
    Get safety net classification for a region based on clinic proximity.
    
    Classifications:
    - COMMUNITY_SUPPORTED: Clinic within threshold distance
    - CRITICAL: No clinic nearby AND unaffordable home internet
    - AT_RISK: No clinic nearby but affordable home internet
    """
    db = SessionLocal()
    try:
        region = CATDataHandler.get_region_by_code(db, region_code)
        if not region or not region.centroid_lat:
            return jsonify({'error': 'Region not found'}), 404
        
        # Determine distance threshold based on access mode
        properties = region.properties or {}
        access_modes = properties.get('primary_access_modes', '')
        
        # Air-only communities need larger radius (50km), road-connected use 10km
        if 'road' in access_modes.lower():
            distance_threshold_km = 10
        else:
            distance_threshold_km = 50  # Air/water access communities
        
        # Find nearby healthcare facilities
        facilities = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None)
        ).all()
        
        # Calculate distances and find nearest clinic
        nearest_clinic = None
        nearest_distance = float('inf')
        
        for facility in facilities:
            dist = _haversine_km(
                region.centroid_lat, region.centroid_lon,
                facility.latitude, facility.longitude
            )
            if dist < nearest_distance and facility.site_type in ['clinic', 'hospital', 'health_center']:
                nearest_distance = dist
                nearest_clinic = facility
        
        has_nearby_clinic = nearest_distance <= distance_threshold_km
        
        # Determine classification
        if has_nearby_clinic:
            classification = 'COMMUNITY_SUPPORTED'
            color = '#f59e0b'  # Amber/orange
            description = f'Healthcare facility within {distance_threshold_km}km provides community anchor'
        else:
            # Check affordability to distinguish CRITICAL from AT_RISK
            # Find nearest ZCTA with income data
            lat_range, lon_range = 0.5, 1.0
            candidate = db.query(CensusIncome).filter(
                CensusIncome.median_income.isnot(None),
                CensusIncome.median_income > 0,
                CensusIncome.centroid_lat.between(region.centroid_lat - lat_range, region.centroid_lat + lat_range),
                CensusIncome.centroid_lon.between(region.centroid_lon - lon_range, region.centroid_lon + lon_range)
            ).first() # Simplified lookup for speed
            
            is_affordable = False
            if candidate:
                cost, _ = _get_regional_internet_cost(candidate.zcta)
                monthly_income = candidate.median_income / 12
                if monthly_income > 0 and (cost / monthly_income) * 100 < 2.0:
                    is_affordable = True

            if is_affordable:
                classification = 'AT_RISK'
                color = '#f97316' # Orange
                description = f'Affordable internet but no nearby healthcare ({distance_threshold_km}km)'
            else:
                classification = 'CRITICAL'
                color = '#ef4444' # Red
                description = f'No healthcare facility within {distance_threshold_km}km and unaffordable internet'
        
        return jsonify({
            'region_code': region_code,
            'region_name': region.region_name,
            'has_nearby_clinic': has_nearby_clinic,
            'distance_threshold_km': distance_threshold_km,
            'access_mode': access_modes or 'unknown',
            'nearest_clinic': {
                'name': nearest_clinic.name if nearest_clinic else None,
                'type': nearest_clinic.site_type if nearest_clinic else None,
                'distance_km': float(f"{nearest_distance:.1f}") if nearest_clinic else None
            } if nearest_clinic else None,
            'classification': classification,
            'classification_color': color,
            'description': description
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/regions/<region_code>/telehealth-status', methods=['GET'])
def get_region_telehealth_status(region_code):
    """
    Get composite telehealth access status for a region.
    
    Uses the canonical Ookla/FCC, affordability, and clinic-access classifier.
    """
    db = SessionLocal()
    try:
        region = CATDataHandler.get_region_by_code(db, region_code)
        if not region:
            return jsonify({'error': 'Region not found'}), 404
        context = TelehealthClassificationService.classify_region(db, region)
        inputs = context.inputs
        classification = context.classification
        return jsonify({
            'region_code': region_code,
            'region_name': region.region_name,
            'status': classification.status,
            'color': classification.color,
            'label': classification.label,
            'description': classification.explanation,
            'affordability': {
                'has_data': classification.affordability_status != 'unknown',
                'is_affordable': (
                    classification.affordability_status == 'affordable'
                    if classification.affordability_status != 'unknown' else None
                ),
                'burden_pct': round(inputs.burden_pct, 2) if inputs.burden_pct is not None else None,
                'internet_cost': inputs.monthly_internet_cost,
            },
            'clinic_proximity': {
                'has_nearby': classification.clinic_supported,
                'nearest_name': context.nearest_clinic.name if context.nearest_clinic else None,
                'nearest_distance_km': (
                    round(inputs.nearest_clinic_distance_km, 1)
                    if inputs.nearest_clinic_distance_km is not None else None
                ),
                'threshold_km': classification.clinic_threshold_km,
            },
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/telehealth-status/all', methods=['GET'])
def get_all_telehealth_status():
    """
    Get composite telehealth status for ALL regions in a single request.
    Used by the Affordability Layer to color all markers at once.
    """
    db = SessionLocal()
    try:
        regions = db.query(CATRegion).all()
        contexts = TelehealthClassificationService.classify_regions(db, regions)
        results = []
        summary = {
            'telehealth_ready': 0,
            'community_anchor': 0,
            'limited_telehealth': 0,
            'critical_gap': 0,
            'data_unavailable': 0,
        }

        for region in regions:
            context = contexts[region.region_code]
            inputs = context.inputs
            classification = context.classification
            summary[classification.status.lower()] += 1
            results.append({
                'region_code': region.region_code,
                'region_name': region.region_name,
                'lat': region.centroid_lat,
                'lon': region.centroid_lon,
                'status': classification.status,
                'color': classification.color,
                'internet_cost': inputs.monthly_internet_cost,
                'isp_name': context.isp_name or 'Unknown',
                'burden_pct': round(inputs.burden_pct, 1) if inputs.burden_pct is not None else None,
                'median_income': inputs.median_income,
                'has_nearby_clinic': classification.clinic_supported,
                'nearest_clinic_name': context.nearest_clinic.name if context.nearest_clinic else None,
                'nearest_clinic_km': (
                    round(inputs.nearest_clinic_distance_km, 1)
                    if inputs.nearest_clinic_distance_km is not None else None
                ),
                'access_mode': inputs.access_modes or 'unknown',
                'recommendation': classification.explanation,
            })

        return jsonify({
            'regions': results,
            'count': len(results),
            'summary': summary
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# =============================================================================
# Healthcare Facility Endpoints
# =============================================================================

@cat_bp.route('/healthcare', methods=['GET'])
def get_healthcare_facilities():
    """
    Get all healthcare facilities with optional filtering.
    
    Query params:
        type: Filter by facility type (hospital, clinic, pharmacy)
        region: Filter by CAT region code
        emergency: Filter to only emergency facilities (true/false)
        limit: Max results to return (default 100)
    """
    db = SessionLocal()
    try:
        query = db.query(HealthcareSite).filter(HealthcareSite.is_active == True)
        
        # Apply filters
        facility_type = request.args.get('type')
        if facility_type:
            query = query.filter(HealthcareSite.site_type == facility_type)
        
        region_code = request.args.get('region')
        if region_code:
            query = query.filter(HealthcareSite.region_code == region_code)
        
        emergency_only = request.args.get('emergency')
        if emergency_only and emergency_only.lower() == 'true':
            query = query.filter(HealthcareSite.has_emergency == True)
        
        limit = request.args.get('limit', 100, type=int)
        sites = query.limit(limit).all()
        
        result = []
        for s in sites:
            result.append({
                'id': s.id,
                'name': s.name,
                'type': s.site_type,
                'latitude': s.latitude,
                'longitude': s.longitude,
                'address': s.address,
                'region_code': s.region_code,
                'has_emergency': s.has_emergency,
                'has_specialists': s.has_specialists,
                'has_telehealth': s.has_telehealth,
                'phone': s.phone,
                'website': s.website,
                'beds': s.beds,
                'services': s.services
            })
        
        # Summary stats
        all_sites = db.query(HealthcareSite).filter(HealthcareSite.is_active == True).all()
        summary = {
            'total': len(all_sites),
            'hospitals': sum(1 for s in all_sites if s.site_type == 'hospital'),
            'clinics': sum(1 for s in all_sites if s.site_type == 'clinic'),
            'pharmacies': sum(1 for s in all_sites if s.site_type == 'pharmacy'),
            'with_emergency': sum(1 for s in all_sites if s.has_emergency),
            'with_telehealth': sum(1 for s in all_sites if s.has_telehealth)
        }
        
        return jsonify({
            'facilities': result,
            'count': len(result),
            'summary': summary
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/healthcare/<int:facility_id>', methods=['GET'])
def get_healthcare_facility(facility_id):
    """Get details for a specific healthcare facility."""
    db = SessionLocal()
    try:
        site = db.query(HealthcareSite).filter(HealthcareSite.id == facility_id).first()
        
        if not site:
            return jsonify({'error': 'Facility not found'}), 404
        
        return jsonify({
            'id': site.id,
            'name': site.name,
            'type': site.site_type,
            'latitude': site.latitude,
            'longitude': site.longitude,
            'address': site.address,
            'region_code': site.region_code,
            'has_emergency': site.has_emergency,
            'has_specialists': site.has_specialists,
            'has_telehealth': site.has_telehealth,
            'phone': site.phone,
            'website': site.website,
            'beds': site.beds,
            'services': site.services,
            'operating_hours': site.operating_hours,
            'is_active': site.is_active,
            'verified': site.verified
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/healthcare/by-region/<region_code>', methods=['GET'])
def get_healthcare_by_region(region_code):
    """
    Get healthcare facilities near a specific region.
    Calculates distance from region centroid to each facility.
    """
    db = SessionLocal()
    try:
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # km
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1-a))
        
        # Get region
        region = db.query(CATRegion).filter(CATRegion.region_code == region_code).first()
        if not region:
            return jsonify({'error': 'Region not found'}), 404
        
        if not region.centroid_lat or not region.centroid_lon:
            return jsonify({'error': 'Region has no centroid coordinates'}), 400
        
        # Get all facilities
        facilities = db.query(HealthcareSite).filter(HealthcareSite.is_active == True).all()
        
        # Calculate distances and sort
        facilities_with_dist = []
        for f in facilities:
            dist = haversine(region.centroid_lat, region.centroid_lon, f.latitude, f.longitude)
            facilities_with_dist.append((f, dist))
        
        # Sort by distance
        facilities_with_dist.sort(key=lambda x: x[1])
        
        # Return top limit nearest
        limit = request.args.get('limit', 20, type=int)
        
        result = []
        for f, dist in list(facilities_with_dist)[:limit]:  # type: ignore
            result.append({
                'id': f.id,
                'name': f.name,
                'type': f.site_type,
                'distance_km': float(f"{dist:.1f}"),
                'latitude': f.latitude,
                'longitude': f.longitude,
                'has_emergency': f.has_emergency,
                'has_specialists': f.has_specialists,
                'phone': f.phone
            })
        
        # Summary - find nearest hospital and clinic with their distances
        nearest_hospital_tuple = next(((f, d) for f, d in facilities_with_dist if f.site_type == 'hospital'), None)
        nearest_clinic_tuple = next(((f, d) for f, d in facilities_with_dist if f.site_type == 'clinic'), None)
        
        return jsonify({
            'region_code': region_code,
            'region_name': region.region_name,
            'facilities': result,
            'count': len(result),
            'nearest_hospital': {
                'name': nearest_hospital_tuple[0].name,
                'distance_km': float(f"{nearest_hospital_tuple[1]:.1f}")
            } if nearest_hospital_tuple else None,
            'nearest_clinic': {
                'name': nearest_clinic_tuple[0].name,
                'distance_km': float(f"{nearest_clinic_tuple[1]:.1f}")
            } if nearest_clinic_tuple else None
        }), 200

        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@cat_bp.route('/healthcare/summary', methods=['GET'])
def get_healthcare_summary():
    """Get overall healthcare coverage summary."""
    db = SessionLocal()
    try:
        facilities = db.query(HealthcareSite).filter(HealthcareSite.is_active == True).all()
        
        summary = {
            'total_facilities': len(facilities),
            'by_type': {
                'hospital': sum(1 for f in facilities if f.site_type == 'hospital'),
                'clinic': sum(1 for f in facilities if f.site_type == 'clinic'),
                'pharmacy': sum(1 for f in facilities if f.site_type == 'pharmacy'),
                'health_center': sum(1 for f in facilities if f.site_type == 'health_center'),
                'other': sum(1 for f in facilities if f.site_type not in ['hospital', 'clinic', 'pharmacy', 'health_center'])
            },
            'features': {
                'with_emergency': sum(1 for f in facilities if f.has_emergency),
                'with_specialists': sum(1 for f in facilities if f.has_specialists),
                'with_telehealth': sum(1 for f in facilities if f.has_telehealth),
                'with_phone': sum(1 for f in facilities if f.phone),
                'with_website': sum(1 for f in facilities if f.website)
            },
            'data_source': 'OpenStreetMap via Overpass Turbo',
            'data_quality': {
                'verified': sum(1 for f in facilities if f.verified),
                'unverified': sum(1 for f in facilities if not f.verified)
            }
        }
        
        return jsonify(summary), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


# =============================================================================
# SCENARIO ANALYSIS
# =============================================================================

@cat_bp.route('/scenarios/preview', methods=['POST'])
def scenario_preview():
    """
    What-if scenario analysis.

    Accepts user-defined thresholds and returns modeled telehealth readiness
    for all (or selected) communities.  Does NOT modify baseline data.

    Request body:
        mode: "preview"
        season: "year_round" | "summer" | "winter"
        thresholds:
            min_download_mbps: number
            min_upload_mbps: number
            max_latency_ms: number | null
            clinic_proximity_km: number | null
            affordability_burden_pct: number
        region_codes: list[str] | null

    Returns scenario summary, per-region status, and deltas vs baseline.
    """
    from services.scenario_engine import ScenarioEngine

    db = SessionLocal()
    try:
        body = request.get_json(silent=True) or {}
        season = body.get('season', SEASON_YEAR_ROUND)
        thresholds_raw = body.get('thresholds', {})
        region_codes = body.get('region_codes')
        if not isinstance(thresholds_raw, dict):
            return jsonify({'error': 'thresholds must be an object'}), 400
        if region_codes is not None:
            if not isinstance(region_codes, list) or not all(isinstance(code, str) for code in region_codes):
                return jsonify({'error': 'region_codes must be a list of strings or null'}), 400

        # Coerce provided threshold values to proper types. Omitted keys should
        # remain omitted so ScenarioEngine can apply baseline defaults.
        thresholds = {}
        for key in ('min_download_mbps', 'min_upload_mbps', 'max_latency_ms',
                     'clinic_proximity_km', 'affordability_burden_pct'):
            if key not in thresholds_raw:
                continue
            value = thresholds_raw.get(key)
            if value is not None:
                try:
                    thresholds[key] = float(value)
                except (TypeError, ValueError):
                    return jsonify({
                        'error': f'Invalid value for {key}: {value!r}'
                    }), 400
            elif key not in ('max_latency_ms', 'clinic_proximity_km'):
                return jsonify({
                    'error': f'{key} cannot be null'
                }), 400
            else:
                thresholds[key] = None

        # Validate
        error = ScenarioEngine.validate_thresholds(thresholds)
        if error:
            return jsonify({'error': error}), 400

        result = ScenarioEngine.preview(
            db,
            thresholds=thresholds,
            season=season,
            region_codes=region_codes,
        )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

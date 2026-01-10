"""
API routes for Community Access Tier (CAT) data management
"""
from database.models import CATRegion, HealthcareSite, CensusIncome
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import math
import json
from database.config import SessionLocal
from database.handlers import CATDataHandler
from services.data_importer import CATDataImporter
from services.healthcare_desert_calculator import HealthcareDesertCalculator
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
                'centroid_lat': region.centroid_lat,
                'centroid_lon': region.centroid_lon,
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
            tier_penalty += 1
            score_penalty += 25
            restricted_modes.append('water (frozen)')
        elif has_water:
            score_penalty += 10
            restricted_modes.append('water (limited)')
        
        # Seasonal roads are unavailable
        if has_road:
            score_penalty += 5  # Roads harder but not impossible
        
        # No air = significant penalty
        if not has_air and base_tier < 4:
            tier_penalty += 1
            score_penalty += 20
        
        adjusted_tier = min(4, base_tier + tier_penalty)
        adjusted_score = max(0, base_score - score_penalty)
        
        if tier_penalty > 0:
            explanation = f"Winter access: {', '.join(restricted_modes) if restricted_modes else 'Limited transport'}"
        else:
            explanation = f"Winter access: Air available; {base_explanation}"
        
        return adjusted_tier, round(adjusted_score, 1), explanation
    
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
        
        adjusted_tier = max(1, base_tier + tier_bonus)
        adjusted_score = min(100, base_score + score_bonus)
        
        if tier_bonus < 0:
            explanation = f"Summer access: Seasonal routes available; improved from Tier {base_tier}"
        elif score_bonus > 0:
            explanation = f"Summer access: All modes available; {base_explanation}"
        else:
            explanation = base_explanation
        
        return adjusted_tier, round(adjusted_score, 1), explanation
    
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
                response['explanation'] = result['failure_reasons'][0]
                # Determine failed gate from explanation
                explanation = response['explanation'].lower()
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
        from database.models import CATDataPoint
        data_point = db.query(CATDataPoint).filter(
            CATDataPoint.region_code == region_code,
            CATDataPoint.is_active == True
        ).first()
        
        if data_point:
            feasibility_result = CATDataHandler.check_cat4_telehealth_feasibility(
                data_point, telehealth_mode='video'
            )
            connectivity_score = 100 if feasibility_result['feasible'] else 0
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
                'feasible_for_video': connectivity_score > 60
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
                    if gap in gap_stats:
                        gap_stats[gap].append({
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
            summary['gap_breakdown'][gap_type] = {
                'count': len(places),
                'percentage': round(len(places) / len(all_records) * 100, 1) if all_records else 0,
                'places': places[:10]  # Return first 10 for each gap type
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

# Load ISP pricing config
def _load_isp_config():
    """Load ISP pricing from config file."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'isp_pricing.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'isp_pricing': {'fastwyre': {'cost': 350}},
            'zcta_mappings': {'gci_urban': [], 'extreme_rural': []},
            'thresholds': {'affordability_burden_pct': 2.0}
        }

_ISP_CONFIG = _load_isp_config()


def _get_regional_internet_cost(zcta: str) -> tuple:
    """Get internet cost for a ZCTA based on regional ISP availability."""
    gci_urban = set(_ISP_CONFIG.get('zcta_mappings', {}).get('gci_urban', []))
    extreme_rural = set(_ISP_CONFIG.get('zcta_mappings', {}).get('extreme_rural', []))
    pricing = _ISP_CONFIG.get('isp_pricing', {})
    
    if zcta in extreme_rural:
        p = pricing.get('extreme_rural', {'cost': 450, 'name': 'Extreme Rural'})
        return (p['cost'], p['name'])
    elif zcta in gci_urban:
        p = pricing.get('gci', {'cost': 125, 'name': 'GCI'})
        return (p['cost'], p['name'])
    else:
        p = pricing.get('fastwyre', {'cost': 350, 'name': 'FastWyre'})
        return (p['cost'], p['name'])


def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers."""
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


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
        
        if not best:
            # No income data found - return unavailable status
            return jsonify({
                'has_income_data': False,
                'income_source': 'unavailable',
                'message': 'No Census income data available for this region',
                'region_code': region_code,
                'region_name': region.region_name
            }), 200
        
        # Calculate affordability
        cost, isp_name = _get_regional_internet_cost(best.zcta)
        monthly_income = best.median_income / 12
        burden_pct = (cost / monthly_income) * 100 if monthly_income > 0 else 100
        threshold = _ISP_CONFIG.get('thresholds', {}).get('affordability_burden_pct', 2.0)
        is_affordable = burden_pct < threshold
        
        return jsonify({
            'has_income_data': True,
            'income_source': 'ZCTA',
            'zcta': best.zcta,
            'distance_km': round(min_dist, 1),
            'median_income': best.median_income,
            'monthly_income': round(monthly_income, 2),
            'internet_cost': cost,
            'isp': isp_name,
            'burden_pct': round(burden_pct, 2),
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
            # For now, if no clinic, mark as CRITICAL (can refine with affordability check)
            classification = 'CRITICAL'
            color = '#ef4444'  # Red
            description = f'No healthcare facility within {distance_threshold_km}km - requires home telehealth'
        
        return jsonify({
            'region_code': region_code,
            'region_name': region.region_name,
            'has_nearby_clinic': has_nearby_clinic,
            'distance_threshold_km': distance_threshold_km,
            'access_mode': access_modes or 'unknown',
            'nearest_clinic': {
                'name': nearest_clinic.name if nearest_clinic else None,
                'type': nearest_clinic.site_type if nearest_clinic else None,
                'distance_km': round(nearest_distance, 1) if nearest_clinic else None
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
    
    Combines affordability and clinic proximity into a single classification:
    - TELEHEALTH_READY (Green): Affordable home internet
    - COMMUNITY_ANCHOR (Yellow/Amber): Unaffordable home, but clinic nearby
    - CRITICAL_GAP (Red): Unaffordable home AND no nearby clinic
    - DATA_UNAVAILABLE (Gray): Cannot determine (missing income data)
    """
    db = SessionLocal()
    try:
        region = CATDataHandler.get_region_by_code(db, region_code)
        if not region or not region.centroid_lat:
            return jsonify({'error': 'Region not found'}), 404
        
        # === STEP 1: Check Affordability ===
        lat_range, lon_range = 0.5, 1.0
        candidates = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.between(region.centroid_lat - lat_range, region.centroid_lat + lat_range),
            CensusIncome.centroid_lon.between(region.centroid_lon - lon_range, region.centroid_lon + lon_range)
        ).all()
        
        best_zcta = None
        min_dist = float('inf')
        for c in candidates:
            if c.centroid_lat and c.centroid_lon:
                dist = _haversine_km(region.centroid_lat, region.centroid_lon, c.centroid_lat, c.centroid_lon)
                if dist < min_dist:
                    min_dist = dist
                    best_zcta = c
        
        has_income_data = best_zcta is not None
        is_affordable = False
        burden_pct = None
        internet_cost = None
        
        if has_income_data:
            internet_cost, isp_name = _get_regional_internet_cost(best_zcta.zcta)
            monthly_income = best_zcta.median_income / 12
            burden_pct = (internet_cost / monthly_income) * 100 if monthly_income > 0 else 100
            threshold = _ISP_CONFIG.get('thresholds', {}).get('affordability_burden_pct', 2.0)
            
            # Absolute cost threshold: $400+/mo is inherently unaffordable regardless of income
            absolute_cost_threshold = 400
            is_affordable = burden_pct < threshold and internet_cost < absolute_cost_threshold
        else:
            # No income data - check if cost is extreme rural ($450+)
            # Get cost based on region location
            region_zcta = region.properties.get('zcta') if region.properties else None
            if region_zcta:
                internet_cost, isp_name = _get_regional_internet_cost(region_zcta)
            else:
                # Default to fastwyre for unknown areas
                internet_cost = 450
                isp_name = 'FastWyre'
        
        # === STEP 2: Check Clinic Proximity ===
        properties = region.properties or {}
        access_modes = properties.get('primary_access_modes', '')
        distance_threshold_km = 10 if 'road' in access_modes.lower() else 50
        
        facilities = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None)
        ).all()
        
        nearest_clinic = None
        nearest_distance = float('inf')
        for f in facilities:
            if f.site_type in ['clinic', 'hospital', 'health_center']:
                dist = _haversine_km(region.centroid_lat, region.centroid_lon, f.latitude, f.longitude)
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_clinic = f
        
        has_nearby_clinic = nearest_distance <= distance_threshold_km
        
        # === STEP 3: Composite Classification ===
        # Check for extreme cost first (>$400/mo is automatically unaffordable)
        is_extreme_cost = internet_cost and internet_cost >= 400
        
        if not has_income_data:
            # Cannot determine affordability by percentage
            if is_extreme_cost:
                # Extreme rural pricing - definitely unaffordable
                if has_nearby_clinic:
                    status = 'COMMUNITY_ANCHOR'
                    color = '#f59e0b'  # Amber
                    label = 'Community Anchor'
                    description = f'Extreme cost (${internet_cost}/mo); clinic provides safety net'
                else:
                    status = 'CRITICAL_GAP'
                    color = '#ef4444'  # Red
                    label = 'Critical Gap'
                    description = f'Extreme cost (${internet_cost}/mo) AND no nearby clinic'
            elif has_nearby_clinic:
                status = 'COMMUNITY_ANCHOR'
                color = '#f59e0b'  # Amber
                label = 'Community Anchor'
                description = 'Income data unavailable; clinic provides safety net'
            else:
                status = 'DATA_UNAVAILABLE'
                color = '#6b7280'  # Gray
                label = 'Data Gap'
                description = 'Cannot assess - no income data and no nearby clinic'
        elif is_affordable:
            status = 'TELEHEALTH_READY'
            color = '#22c55e'  # Green
            label = 'Telehealth Ready'
            description = f'Home internet affordable ({burden_pct:.1f}% of income)'
        elif has_nearby_clinic:
            status = 'COMMUNITY_ANCHOR'
            color = '#f59e0b'  # Amber/Yellow
            label = 'Community Anchor'
            description = f'Home internet unaffordable ({burden_pct:.1f}%), but clinic {nearest_distance:.1f}km away'
        else:
            status = 'CRITICAL_GAP'
            color = '#ef4444'  # Red
            label = 'Critical Gap'
            description = f'Home internet unaffordable ({burden_pct:.1f}%) AND no clinic within {distance_threshold_km}km'
        
        return jsonify({
            'region_code': region_code,
            'region_name': region.region_name,
            'status': status,
            'color': color,
            'label': label,
            'description': description,
            'affordability': {
                'has_data': has_income_data,
                'is_affordable': is_affordable,
                'burden_pct': round(burden_pct, 2) if burden_pct else None,
                'internet_cost': internet_cost
            },
            'clinic_proximity': {
                'has_nearby': has_nearby_clinic,
                'nearest_name': nearest_clinic.name if nearest_clinic else None,
                'nearest_distance_km': round(nearest_distance, 1) if nearest_clinic else None,
                'threshold_km': distance_threshold_km
            }
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
        
        # Pre-fetch all census and healthcare data for efficiency
        all_census = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0
        ).all()
        
        all_facilities = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None)
        ).all()
        
        # Filter to clinics/hospitals only
        clinics = [f for f in all_facilities if f.site_type in ['clinic', 'hospital', 'health_center']]
        
        results = []
        summary = {'telehealth_ready': 0, 'community_anchor': 0, 'critical_gap': 0, 'data_unavailable': 0}
        
        for region in regions:
            if not region.centroid_lat or not region.centroid_lon:
                continue
            
            # Find nearest ZCTA with income
            best_zcta = None
            min_dist = float('inf')
            for c in all_census:
                if c.centroid_lat and c.centroid_lon:
                    dist = _haversine_km(region.centroid_lat, region.centroid_lon, c.centroid_lat, c.centroid_lon)
                    if dist < min_dist and dist < 55:  # 55km threshold
                        min_dist = dist
                        best_zcta = c
            
            has_income_data = best_zcta is not None
            is_affordable = False
            burden_pct = None
            internet_cost = None
            median_income = None
            isp_name = 'Unknown'
            
            if has_income_data:
                internet_cost, isp_name = _get_regional_internet_cost(best_zcta.zcta)
                median_income = best_zcta.median_income
                monthly_income = best_zcta.median_income / 12
                burden_pct = (internet_cost / monthly_income) * 100 if monthly_income > 0 else 100
                threshold = _ISP_CONFIG.get('thresholds', {}).get('affordability_burden_pct', 2.0)
                is_affordable = burden_pct < threshold and internet_cost < 400
            else:
                internet_cost = 450  # Default fastwyre
                isp_name = 'FastWyre (est.)'
            
            # Find nearest clinic
            properties = region.properties or {}
            access_modes = properties.get('primary_access_modes', '')
            distance_threshold_km = 10 if 'road' in access_modes.lower() else 50
            
            nearest_distance = float('inf')
            nearest_clinic_name = None
            for f in clinics:
                dist = _haversine_km(region.centroid_lat, region.centroid_lon, f.latitude, f.longitude)
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_clinic_name = f.name
            
            has_nearby_clinic = nearest_distance <= distance_threshold_km
            is_extreme_cost = internet_cost and internet_cost >= 400
            
            # Classification + Recommendation
            if not has_income_data:
                if is_extreme_cost:
                    # $450+/mo is inherently unaffordable - mark as such even without income data
                    if has_nearby_clinic:
                        status, color = 'COMMUNITY_ANCHOR', '#f59e0b'
                        recommendation = f'Extreme cost (${internet_cost}/mo) - use community clinic for telehealth'
                    else:
                        status, color = 'CRITICAL_GAP', '#ef4444'
                        recommendation = f'UNAFFORDABLE (${internet_cost}/mo) + No clinic access - urgent intervention needed'
                elif has_nearby_clinic:
                    status, color = 'COMMUNITY_ANCHOR', '#f59e0b'
                    recommendation = 'Use community clinic for telehealth access'
                else:
                    status, color = 'DATA_UNAVAILABLE', '#6b7280'
                    recommendation = 'Collect income data to assess affordability'
            elif is_affordable:
                status, color = 'TELEHEALTH_READY', '#22c55e'
                recommendation = 'Home-based telehealth is viable'
            elif has_nearby_clinic:
                status, color = 'COMMUNITY_ANCHOR', '#f59e0b'
                recommendation = 'Use community clinic for telehealth access'
            else:
                status, color = 'CRITICAL_GAP', '#ef4444'
                recommendation = f'UNAFFORDABLE ({burden_pct:.1f}% burden) + No clinic - urgent intervention needed'
            
            # Update summary
            summary[status.lower()] = summary.get(status.lower(), 0) + 1
            
            results.append({
                'region_code': region.region_code,
                'region_name': region.region_name,
                'lat': region.centroid_lat,
                'lon': region.centroid_lon,
                'status': status,
                'color': color,
                'internet_cost': internet_cost,
                'isp_name': isp_name,
                'burden_pct': round(burden_pct, 1) if burden_pct else None,
                'median_income': median_income,
                'has_nearby_clinic': has_nearby_clinic,
                'nearest_clinic_name': nearest_clinic_name,
                'nearest_clinic_km': round(nearest_distance, 1) if nearest_distance != float('inf') else None,
                'access_mode': access_modes or 'unknown',
                'recommendation': recommendation
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
        
        # Return top 20 nearest
        limit = request.args.get('limit', 20, type=int)
        result = []
        for f, dist in facilities_with_dist[:limit]:
            result.append({
                'id': f.id,
                'name': f.name,
                'type': f.site_type,
                'distance_km': round(dist, 1),
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
                'distance_km': round(nearest_hospital_tuple[1], 1)
            } if nearest_hospital_tuple else None,
            'nearest_clinic': {
                'name': nearest_clinic_tuple[0].name,
                'distance_km': round(nearest_clinic_tuple[1], 1)
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


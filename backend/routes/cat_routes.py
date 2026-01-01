"""
API routes for Community Access Tier (CAT) data management
"""
from database.models import CATRegion, HealthcareSite
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
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


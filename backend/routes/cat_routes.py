"""
API routes for Community Access Tier (CAT) data management
"""
from database.models import CATRegion
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from database.config import SessionLocal
from database.handlers import CATDataHandler
from services.data_importer import CATDataImporter

cat_bp = Blueprint('cat', __name__, url_prefix='/api/cat')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'uploads')
ALLOWED_EXTENSIONS = {'csv', 'geojson', 'json'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Region endpoints
@cat_bp.route('/regions', methods=['GET'])
def get_regions():
    """Get all regions or filter by tier"""


@cat_bp.route('/regions/<region_code>', methods=['GET'])
def get_region(region_code):
    """Get specific region by code"""
    
    db = SessionLocal()
    try:
        tier_level = request.args.get('tier', type=int)

        if tier_level:
            regions = CATDataHandler.get_regions_by_tier(db, tier_level)
        else:
            
            regions = db.query(CATRegion).all()

        result = []
        for region in regions:
            result.append({
                'id': region.id,
                'region_name': region.region_name,
                'region_code': region.region_code,
                'tier_level': region.tier_level,
                'population': region.population,
                'area_sqkm': region.area_sqkm,
                'access_score': region.access_score,
                'created_at': region.created_at.isoformat() if region.created_at else None
            })

        return jsonify({'regions': result, 'count': len(result)}), 200

    except Exception as e:
        # optionally: db.rollback() if you use transactions
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

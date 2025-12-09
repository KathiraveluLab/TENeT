"""
Database handler for CAT (Community Access Tier) operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict
from datetime import datetime
import json

from database.models import CATRegion, CATDataPoint, CATUpload, CATGatingRule


class CATDataHandler:
    """Handler for CAT data operations"""
    
    @staticmethod
    def create_region(db: Session, region_data: dict) -> CATRegion:
        """Create a new CAT region"""
        region = CATRegion(**region_data)
        db.add(region)
        db.commit()
        db.refresh(region)
        return region
    
    @staticmethod
    def get_region_by_code(db: Session, region_code: str) -> Optional[CATRegion]:
        """Get region by code"""
        return db.query(CATRegion).filter(CATRegion.region_code == region_code).first()
    
    @staticmethod
    def get_regions_by_tier(db: Session, tier_level: int) -> List[CATRegion]:
        """Get all regions for a specific tier"""
        return db.query(CATRegion).filter(CATRegion.tier_level == tier_level).all()
    
    @staticmethod
    def create_data_point(db: Session, point_data: dict) -> CATDataPoint:
        """Create a new data point"""
        data_point = CATDataPoint(**point_data)
        db.add(data_point)
        db.commit()
        db.refresh(data_point)
        return data_point
    
    @staticmethod
    def bulk_create_data_points(db: Session, points_data: List[dict]) -> int:
        """Bulk create data points"""
        data_points = [CATDataPoint(**point) for point in points_data]
        db.bulk_save_objects(data_points)
        db.commit()
        return len(data_points)
    
    @staticmethod
    def get_data_points_by_region(db: Session, region_code: str, 
                                   access_type: Optional[str] = None) -> List[CATDataPoint]:
        """Get all data points for a region"""
        query = db.query(CATDataPoint).filter(CATDataPoint.region_code == region_code)
        if access_type:
            query = query.filter(CATDataPoint.access_type == access_type)
        return query.all()
    
    @staticmethod
    def get_data_points_in_radius(db: Session, lat: float, lon: float, 
                                   radius_km: float) -> List[CATDataPoint]:
        """Get data points within radius (simple distance calculation)"""
        # Simple bounding box calculation (for precise distance, use PostGIS)
        lat_delta = radius_km / 111.0  # 1 degree latitude ≈ 111 km
        lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
        
        return db.query(CATDataPoint).filter(
            and_(
                CATDataPoint.latitude >= lat - lat_delta,
                CATDataPoint.latitude <= lat + lat_delta,
                CATDataPoint.longitude >= lon - lon_delta,
                CATDataPoint.longitude <= lon + lon_delta,
                CATDataPoint.is_active == True
            )
        ).all()
    
    @staticmethod
    def create_upload_record(db: Session, upload_data: dict) -> CATUpload:
        """Create upload tracking record"""
        upload = CATUpload(**upload_data)
        db.add(upload)
        db.commit()
        db.refresh(upload)
        return upload
    
    @staticmethod
    def update_upload_status(db: Session, upload_id: int, status: str, 
                            records_processed: int = 0, error_message: str = None):
        """Update upload processing status"""
        upload = db.query(CATUpload).filter(CATUpload.id == upload_id).first()
        if upload:
            upload.status = status
            upload.records_processed = records_processed
            upload.error_message = error_message
            if status == 'completed':
                upload.processed_date = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def create_gating_rule(db: Session, rule_data: dict) -> CATGatingRule:
        """Create a new gating rule"""
        rule = CATGatingRule(**rule_data)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule
    
    @staticmethod
    def get_active_gating_rules(db: Session, tier_level: Optional[int] = None) -> List[CATGatingRule]:
        """Get active gating rules"""
        query = db.query(CATGatingRule).filter(CATGatingRule.is_active == True)
        if tier_level:
            query = query.filter(CATGatingRule.tier_level == tier_level)
        return query.order_by(CATGatingRule.priority.desc()).all()
    
    @staticmethod
    def check_access_gating(db: Session, data_point: CATDataPoint, 
                           tier_level: int) -> Dict:
        """Check if data point passes gating rules"""
        rules = CATDataHandler.get_active_gating_rules(db, tier_level)
        
        result = {
            'allowed': True,
            'failed_rules': [],
            'passed_rules': []
        }
        
        for rule in rules:
            passed = True
            reason = []
            
            # Check minimum access score
            if rule.min_access_score and data_point.access_quality:
                if data_point.access_quality < rule.min_access_score:
                    passed = False
                    reason.append(f"Access quality {data_point.access_quality} below minimum {rule.min_access_score}")
            
            # Check maximum distance
            if rule.max_distance_km and data_point.distance_km:
                if data_point.distance_km > rule.max_distance_km:
                    passed = False
                    reason.append(f"Distance {data_point.distance_km}km exceeds maximum {rule.max_distance_km}km")
            
            # Check maximum travel time
            if rule.max_travel_time and data_point.travel_time_minutes:
                if data_point.travel_time_minutes > rule.max_travel_time:
                    passed = False
                    reason.append(f"Travel time {data_point.travel_time_minutes}min exceeds maximum {rule.max_travel_time}min")
            
            # Check access types
            if rule.access_types and data_point.access_type:
                if data_point.access_type not in rule.access_types:
                    passed = False
                    reason.append(f"Access type '{data_point.access_type}' not in allowed types")
            
            if passed:
                result['passed_rules'].append(rule.rule_name)
            else:
                result['allowed'] = False
                result['failed_rules'].append({
                    'rule': rule.rule_name,
                    'reasons': reason
                })
        
        return result
    
    @staticmethod
    def get_statistics(db: Session) -> dict:
        """Get database statistics"""
        return {
            'total_regions': db.query(CATRegion).count(),
            'total_uploads': db.query(CATUpload).count(),
            'total_data_points': db.query(CATDataPoint).count(),
            'completed_uploads': db.query(CATUpload).filter(CATUpload.status == 'completed').count(),
            'total_gating_rules': db.query(CATGatingRule).count(),
            'active_gating_rules': db.query(CATGatingRule).filter(CATGatingRule.is_active == True).count()
        }

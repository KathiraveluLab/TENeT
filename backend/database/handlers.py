"""
Database handler for CAT (Community Access Tier) operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict
from datetime import datetime
import json
import math

from database.models import CATRegion, CATDataPoint, CATUpload, CATGatingRule


# =============================================================================
# CAT-4 Telehealth Feasibility Thresholds
# =============================================================================
# CAT-4 represents extreme friction regions (fly-in only, e.g., Little Diomede)
# These thresholds enforce HARD FAIL conditions - no averaging or trade-offs allowed

# Minimum bandwidth for ANY telehealth mode (Mbps)
CAT4_MIN_BANDWIDTH_MBPS = 1.5

# Maximum acceptable latency for audio/general telehealth (ms)
# Based on satellite communication tolerance
CAT4_MAX_LATENCY_MS = 600

# Minimum access reliability score (0-100 scale)
CAT4_MIN_ACCESS_SCORE = 30.0

# Real-time video specific thresholds (stricter)
CAT4_VIDEO_MIN_BANDWIDTH_MBPS = 4.0
CAT4_VIDEO_MAX_LATENCY_MS = 300

# Store-and-forward thresholds (most lenient)
CAT4_STORE_FORWARD_MIN_BANDWIDTH_MBPS = 0.5

# Telehealth modes
TELEHEALTH_MODE_VIDEO = 'video'
TELEHEALTH_MODE_AUDIO = 'audio'
TELEHEALTH_MODE_STORE_FORWARD = 'store_forward'


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
        from database.models import HealthcareSite
        
        return {
            'total_regions': db.query(CATRegion).count(),
            'total_uploads': db.query(CATUpload).count(),
            'total_data_points': db.query(CATDataPoint).count(),
            'completed_uploads': db.query(CATUpload).filter(CATUpload.status == 'completed').count(),
            'total_gating_rules': db.query(CATGatingRule).count(),
            'active_gating_rules': db.query(CATGatingRule).filter(CATGatingRule.is_active == True).count(),
            'total_healthcare_sites': db.query(HealthcareSite).count(),
            'hospitals': db.query(HealthcareSite).filter(HealthcareSite.site_type == 'hospital').count(),
            'clinics': db.query(HealthcareSite).filter(HealthcareSite.site_type == 'clinic').count()
        }
    
    # =========================================================================
    # CAT-4 Telehealth Feasibility Evaluation
    # =========================================================================
    
    @staticmethod
    def check_cat4_telehealth_feasibility(data_point: CATDataPoint, 
                                          telehealth_mode: Optional[str] = None) -> Dict:
        """
        Evaluate telehealth feasibility for CAT-4 (Fly-in Only / Extreme Friction) regions.
        
        CAT-4 represents the most constrained environments (e.g., Little Diomede),
        where telehealth feasibility must be evaluated conservatively with HARD CONSTRAINTS.
        
        CRITICAL: This function implements HARD FAIL conditions.
        - Any threshold breach = NOT FEASIBLE
        - No compensating trade-offs (no averaging, no soft scoring)
        
        Args:
            data_point: CATDataPoint containing network metrics (throughput_mbps, latency_ms, access_quality)
            telehealth_mode: Optional specific mode to evaluate ('video', 'audio', 'store_forward')
                           If None, evaluates all modes
        
        Returns:
            Dict with:
                - feasible: Boolean indicating overall feasibility
                - mode_results: Dict with per-mode feasibility results
                - failure_reasons: List of human-readable failure messages
                - evaluated_mode: The mode(s) evaluated
        """
        result = {
            'feasible': False,
            'mode_results': {
                TELEHEALTH_MODE_VIDEO: {'feasible': False, 'failure_reasons': []},
                TELEHEALTH_MODE_AUDIO: {'feasible': False, 'failure_reasons': []},
                TELEHEALTH_MODE_STORE_FORWARD: {'feasible': False, 'failure_reasons': []}
            },
            'failure_reasons': [],
            'evaluated_mode': telehealth_mode or 'all'
        }
        
        # Extract network metrics from data point
        bandwidth = data_point.throughput_mbps
        latency = data_point.latency_ms
        access_score = data_point.access_quality
        
        # ---------------------------------------------------------------------
        # HARD FAIL: Check core access score (applies to ALL modes)
        # ---------------------------------------------------------------------
        if access_score is not None and access_score < CAT4_MIN_ACCESS_SCORE:
            failure_msg = f"Access score {access_score} below CAT-4 minimum ({CAT4_MIN_ACCESS_SCORE})"
            result['failure_reasons'].append(failure_msg)
            # Mark all modes as failed due to access score
            for mode in result['mode_results']:
                result['mode_results'][mode]['failure_reasons'].append(failure_msg)
            # Return early - access score failure affects all modes
            return result
        
        # ---------------------------------------------------------------------
        # Evaluate VIDEO mode (strictest requirements)
        # ---------------------------------------------------------------------
        video_result = result['mode_results'][TELEHEALTH_MODE_VIDEO]
        video_feasible = True
        
        # Check bandwidth for video
        if bandwidth is None:
            video_result['failure_reasons'].append("Bandwidth data unavailable for video evaluation")
            video_feasible = False
        elif bandwidth < CAT4_VIDEO_MIN_BANDWIDTH_MBPS:
            video_result['failure_reasons'].append(
                f"Bandwidth {bandwidth} Mbps below CAT-4 video minimum ({CAT4_VIDEO_MIN_BANDWIDTH_MBPS} Mbps)"
            )
            video_feasible = False
        
        # Check latency for video
        if latency is None:
            video_result['failure_reasons'].append("Latency data unavailable for video evaluation")
            video_feasible = False
        elif latency > CAT4_VIDEO_MAX_LATENCY_MS:
            video_result['failure_reasons'].append(
                f"Latency {latency} ms exceeds CAT-4 video maximum ({CAT4_VIDEO_MAX_LATENCY_MS} ms)"
            )
            video_feasible = False
        
        video_result['feasible'] = video_feasible
        
        # ---------------------------------------------------------------------
        # Evaluate AUDIO mode (moderate requirements)
        # ---------------------------------------------------------------------
        audio_result = result['mode_results'][TELEHEALTH_MODE_AUDIO]
        audio_feasible = True
        
        # Check bandwidth for audio
        if bandwidth is None:
            audio_result['failure_reasons'].append("Bandwidth data unavailable for audio evaluation")
            audio_feasible = False
        elif bandwidth < CAT4_MIN_BANDWIDTH_MBPS:
            audio_result['failure_reasons'].append(
                f"Bandwidth {bandwidth} Mbps below CAT-4 audio minimum ({CAT4_MIN_BANDWIDTH_MBPS} Mbps)"
            )
            audio_feasible = False
        
        # Check latency for audio (uses general CAT-4 latency limit)
        if latency is None:
            audio_result['failure_reasons'].append("Latency data unavailable for audio evaluation")
            audio_feasible = False
        elif latency > CAT4_MAX_LATENCY_MS:
            audio_result['failure_reasons'].append(
                f"Latency {latency} ms exceeds satellite tolerance ({CAT4_MAX_LATENCY_MS} ms)"
            )
            audio_feasible = False
        
        audio_result['feasible'] = audio_feasible
        
        # ---------------------------------------------------------------------
        # Evaluate STORE-AND-FORWARD mode (most lenient)
        # ---------------------------------------------------------------------
        store_forward_result = result['mode_results'][TELEHEALTH_MODE_STORE_FORWARD]
        store_forward_feasible = True
        
        # Check bandwidth for store-and-forward (lowest requirement)
        if bandwidth is None:
            store_forward_result['failure_reasons'].append("Bandwidth data unavailable for store-forward evaluation")
            store_forward_feasible = False
        elif bandwidth < CAT4_STORE_FORWARD_MIN_BANDWIDTH_MBPS:
            store_forward_result['failure_reasons'].append(
                f"Bandwidth {bandwidth} Mbps below store-forward minimum ({CAT4_STORE_FORWARD_MIN_BANDWIDTH_MBPS} Mbps)"
            )
            store_forward_feasible = False
        
        # Note: Store-and-forward has NO latency requirement (asynchronous by nature)
        
        store_forward_result['feasible'] = store_forward_feasible
        
        # ---------------------------------------------------------------------
        # Determine overall feasibility based on requested mode
        # ---------------------------------------------------------------------
        if telehealth_mode == TELEHEALTH_MODE_VIDEO:
            result['feasible'] = video_feasible
            if not video_feasible:
                result['failure_reasons'] = video_result['failure_reasons']
        elif telehealth_mode == TELEHEALTH_MODE_AUDIO:
            result['feasible'] = audio_feasible
            if not audio_feasible:
                result['failure_reasons'] = audio_result['failure_reasons']
        elif telehealth_mode == TELEHEALTH_MODE_STORE_FORWARD:
            result['feasible'] = store_forward_feasible
            if not store_forward_feasible:
                result['failure_reasons'] = store_forward_result['failure_reasons']
        else:
            # No specific mode requested - feasible if ANY mode works
            result['feasible'] = video_feasible or audio_feasible or store_forward_feasible
            if not result['feasible']:
                result['failure_reasons'] = [
                    "No telehealth mode feasible for this CAT-4 location",
                    *store_forward_result['failure_reasons']  # Show most lenient mode's failures
                ]
        
        return result

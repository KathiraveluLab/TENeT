"""
Service for importing CAT data from CSV and GeoJSON files
"""
import pandas as pd
import geopandas as gpd
import json
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from shapely.geometry import shape, mapping
import os

from database.handlers import CATDataHandler


class CATDataImporter:
    """Import CAT data from various file formats"""
    
    @staticmethod
    def import_csv(db: Session, file_path: str, upload_id: int = None) -> Tuple[int, str]:
        """
        Import data points from CSV file
        Expected columns: region_code, latitude, longitude, location_name, 
                         access_type, access_quality, distance_km, travel_time_minutes
        """
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_cols = ['region_code', 'latitude', 'longitude']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                error_msg = f"Missing required columns: {', '.join(missing_cols)}"
                if upload_id:
                    CATDataHandler.update_upload_status(db, upload_id, 'failed', 0, error_msg)
                return 0, error_msg
            
            # Update upload status to processing
            if upload_id:
                CATDataHandler.update_upload_status(db, upload_id, 'processing')
            
            # Prepare data points
            data_points = []
            for _, row in df.iterrows():
                point_data = {
                    'region_code': str(row['region_code']),
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'location_name': row.get('location_name'),
                    'access_type': row.get('access_type'),
                    'access_quality': float(row['access_quality']) if pd.notna(row.get('access_quality')) else None,
                    'distance_km': float(row['distance_km']) if pd.notna(row.get('distance_km')) else None,
                    'travel_time_minutes': float(row['travel_time_minutes']) if pd.notna(row.get('travel_time_minutes')) else None,
                    'is_active': True,
                    'verified': False
                }
                
                # Store additional columns as metadata
                extra_cols = [col for col in df.columns if col not in [
                    'region_code', 'latitude', 'longitude', 'location_name',
                    'access_type', 'access_quality', 'distance_km', 'travel_time_minutes'
                ]]
                if extra_cols:
                    point_data['metadata'] = {col: row[col] for col in extra_cols if pd.notna(row[col])}
                
                data_points.append(point_data)
            
            # Bulk insert
            count = CATDataHandler.bulk_create_data_points(db, data_points)
            
            # Update upload status
            if upload_id:
                CATDataHandler.update_upload_status(db, upload_id, 'completed', count)
            
            return count, f"Successfully imported {count} data points"
            
        except Exception as e:
            error_msg = f"Error importing CSV: {str(e)}"
            if upload_id:
                CATDataHandler.update_upload_status(db, upload_id, 'failed', 0, error_msg)
            return 0, error_msg
    
    @staticmethod
    def import_geojson(db: Session, file_path: str, upload_id: int = None) -> Tuple[int, str]:
        """
        Import regions from GeoJSON file
        Expected properties: region_name, region_code, tier_level, population, area_sqkm
        """
        try:
            from geoalchemy2.shape import from_shape
            from shapely.geometry import shape
            
            # Read GeoJSON
            gdf = gpd.read_file(file_path)
            
            # Validate required properties
            required_props = ['region_name', 'region_code', 'tier_level']
            missing_props = [prop for prop in required_props if prop not in gdf.columns]
            if missing_props:
                error_msg = f"Missing required properties: {', '.join(missing_props)}"
                if upload_id:
                    CATDataHandler.update_upload_status(db, upload_id, 'failed', 0, error_msg)
                return 0, error_msg
            
            # Update upload status to processing
            if upload_id:
                CATDataHandler.update_upload_status(db, upload_id, 'processing')
            
            # Import regions
            count = 0
            for _, row in gdf.iterrows():
                # Convert geometry to PostGIS-compatible format
                geom_wkt = from_shape(row.geometry, srid=4326)
                
                region_data = {
                    'region_name': str(row['region_name']),
                    'region_code': str(row['region_code']),
                    'tier_level': int(row['tier_level']),
                    'geometry': geom_wkt,
                    'population': int(row['population']) if 'population' in row and pd.notna(row['population']) else None,
                    'area_sqkm': float(row['area_sqkm']) if 'area_sqkm' in row and pd.notna(row['area_sqkm']) else None,
                    'access_score': float(row['access_score']) if 'access_score' in row and pd.notna(row['access_score']) else None,
                }
                
                # Store additional properties as JSON
                extra_props = [col for col in gdf.columns if col not in [
                    'region_name', 'region_code', 'tier_level', 'geometry',
                    'population', 'area_sqkm', 'access_score'
                ]]
                if extra_props:
                    region_data['properties'] = {col: row[col] for col in extra_props if pd.notna(row[col])}
                
                # Check if region exists
                existing = CATDataHandler.get_region_by_code(db, region_data['region_code'])
                if not existing:
                    CATDataHandler.create_region(db, region_data)
                    count += 1
            
            # Update upload status
            if upload_id:
                CATDataHandler.update_upload_status(db, upload_id, 'completed', count)
            
            return count, f"Successfully imported {count} regions"
            
        except Exception as e:
            error_msg = f"Error importing GeoJSON: {str(e)}"
            if upload_id:
                CATDataHandler.update_upload_status(db, upload_id, 'failed', 0, error_msg)
            return 0, error_msg
    
    @staticmethod
    def export_to_csv(db: Session, region_code: str = None, output_path: str = None) -> str:
        """Export data points to CSV"""
        try:
            if region_code:
                data_points = CATDataHandler.get_data_points_by_region(db, region_code)
            else:
                data_points = db.query(CATDataPoint).all()
            
            # Convert to DataFrame
            data = []
            for point in data_points:
                row = {
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
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            
            # Save to CSV
            if not output_path:
                output_path = f"cat_data_export_{region_code or 'all'}.csv"
            
            df.to_csv(output_path, index=False)
            return output_path
            
        except Exception as e:
            raise Exception(f"Error exporting to CSV: {str(e)}")
    
    @staticmethod
    def export_to_geojson(db: Session, tier_level: int = None, output_path: str = None) -> str:
        """Export regions to GeoJSON"""
        try:
            if tier_level:
                regions = CATDataHandler.get_regions_by_tier(db, tier_level)
            else:
                regions = db.query(CATRegion).all()
            
            # Build GeoJSON features
            features = []
            for region in regions:
                if region.geometry:
                    geom = json.loads(region.geometry)
                    feature = {
                        'type': 'Feature',
                        'geometry': geom,
                        'properties': {
                            'id': region.id,
                            'region_name': region.region_name,
                            'region_code': region.region_code,
                            'tier_level': region.tier_level,
                            'population': region.population,
                            'area_sqkm': region.area_sqkm,
                            'access_score': region.access_score
                        }
                    }
                    features.append(feature)
            
            geojson = {
                'type': 'FeatureCollection',
                'features': features
            }
            
            # Save to file
            if not output_path:
                output_path = f"cat_regions_export_tier{tier_level or 'all'}.geojson"
            
            with open(output_path, 'w') as f:
                json.dump(geojson, f, indent=2)
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Error exporting to GeoJSON: {str(e)}")


# Import CATDataPoint for export functions
from database.models import CATDataPoint, CATRegion

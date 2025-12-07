TENeT Database Setup Guide
Overview
The TENeT project utilizes a lightweight SQLite database with geospatial support to manage Community Access Tier (CAT) data. This system enables the import, management, and querying of CSV and GeoJSON data without requiring PostgreSQL or PostGIS infrastructure.

Database Architecture
Table Structure
The database consists of four primary tables:
cat_regions stores geographic regions with their associated tier classifications. cat_data_points maintains individual access points including healthcare facilities, educational institutions, and transportation hubs. cat_uploads tracks file upload history and processing status. cat_gating_rules defines access control criteria organized by tier level.

File Locations
Development database: backend/data/tenet.db
Upload directory: backend/data/uploads/
Sample data: backend/data/samples/

Installation and Setup
Dependency Installation
Navigate to the backend directory and install the required dependencies:

cd backend
pip install -r requirements.txt
Database Initialization
Execute the initialization script to create the database schema:

python database/init_db.py
This command will create all required tables, establish three sample gating rules (Tier 1, 2, and 3), and display initial database statistics.

Sample Data Import
To test the system with sample data, use the following commands:
Import sample regions (GeoJSON format):

curl -X POST http://localhost:5000/api/cat/upload \
-F "file=@data/samples/sample_cat_regions.geojson"
Import sample data points (CSV format):

curl -X POST http://localhost:5000/api/cat/upload \
-F "file=@data/samples/sample_cat_data.csv"
API Reference
Region Endpoints
Retrieve all regions: GET /api/cat/regions
Filter regions by tier: GET /api/cat/regions?tier=1
Retrieve specific region: GET /api/cat/regions/{region_code}

Data Point Endpoints
Retrieve all data points: GET /api/cat/data-points (maximum 100 results per request)
Filter by region: GET /api/cat/data-points?region_code=AK001
Radius-based search: GET /api/cat/data-points?lat=61.2181&lon=-149.9003&radius_km=10
Filter by access type: GET /api/cat/data-points?access_type=healthcare

Upload Management
Upload data files: POST /api/cat/upload
Supported formats: .csv, .geojson, .json
Files are automatically processed and imported upon upload.

Gating Rule Management
Retrieve all active rules: GET /api/cat/gating/rules
Filter rules by tier: GET /api/cat/gating/rules?tier=2
Create new rule: POST /api/cat/gating/rules
Validate against rules: POST /api/cat/gating/check

Statistical Information
Retrieve database statistics: GET /api/cat/statistics

Data Format Specifications
CSV Format Requirements
Required columns:

region_code - Region identifier
latitude - Decimal degrees
longitude - Decimal degrees
Optional columns:

location_name - Location designation
access_type - Service category (healthcare, education, transport, etc.)
access_quality - Quality metric (0-100 scale)
distance_km - Distance measurement in kilometers
travel_time_minutes - Estimated travel duration in minutes
Example structure:

region_code,latitude,longitude,location_name,access_type,access_quality,distance_km,travel_time_minutes
AK001,61.2181,-149.9003,Anchorage Medical Center,healthcare,85.5,2.3,15
GeoJSON Format Requirements
Required properties:

region_name - Region designation
region_code - Unique region identifier
tier_level - Tier classification (1, 2, or 3)
Optional properties:

population - Population count
area_sqkm - Area measurement in square kilometers
access_score - Aggregate access metric
Example structure:

{
"type": "Feature",
"geometry": {
"type": "Polygon",
"coordinates": [[[-150.0, 61.0], [-149.5, 61.0], [-149.5, 61.5], [-150.0, 61.5], [-150.0, 61.0]]]
},
"properties": {
"region_name": "Anchorage Region",
"region_code": "AK001",
"tier_level": 1,
"population": 291538,
"area_sqkm": 5079.0,
"access_score": 85.0
}
}
Access Tier Classification System
Tier Definitions
Tier 1 (High Access) represents urban areas with well-developed infrastructure. Classification criteria include a minimum access score of 60.0, maximum distance of 50 kilometers, and maximum travel time of 60 minutes.
Tier 2 (Moderate Access) encompasses suburban areas and small cities. Requirements include a minimum access score of 40.0, maximum distance of 100 kilometers, and maximum travel time of 120 minutes.
Tier 3 (Limited Access) designates rural and remote areas. Criteria include a minimum access score of 20.0, maximum distance of 200 kilometers, and maximum travel time of 180 minutes.

Gating Rule Validation
To validate a data point against tier criteria:

curl -X POST http://localhost:5000/api/cat/gating/check \
-H "Content-Type: application/json" \
-d '{
"point_id": 1,
"tier_level": 2
}'
Expected response:

{
"allowed": true,
"passed_rules": ["Tier 2 Moderate Access"],
"failed_rules": []
}
Programmatic Data Management
Data Import Operations
from database.config import SessionLocal
from services.data_importer import CATDataImporter

db = SessionLocal()

# CSV import operation
count, message = CATDataImporter.import_csv(
db,
'data/samples/sample_cat_data.csv'
)
print(f"Imported {count} data points")

# GeoJSON import operation
count, message = CATDataImporter.import_geojson(
db,
'data/samples/sample_cat_regions.geojson'
)
print(f"Imported {count} regions")

db.close()
Data Query Operations
from database.config import SessionLocal
from database.handlers import CATDataHandler

db = SessionLocal()

# Retrieve regions by tier level
regions = CATDataHandler.get_regions_by_tier(db, tier_level=1)
for region in regions:
print(f"{region.region_name} - Tier {region.tier_level}")

# Retrieve data points by region code
points = CATDataHandler.get_data_points_by_region(db, 'AK001')
print(f"Retrieved {len(points)} data points in region AK001")

# Perform radius-based search
nearby = CATDataHandler.get_data_points_in_radius(
db,
lat=61.2181,
lon=-149.9003,
radius_km=10
)
print(f"Located {len(nearby)} points within 10-kilometer radius")

db.close()
Data Export Operations
from database.config import SessionLocal
from services.data_importer import CATDataImporter

db = SessionLocal()

# Export to CSV format
csv_path = CATDataImporter.export_to_csv(db, region_code='AK001')
print(f"Data exported to {csv_path}")

# Export to GeoJSON format
geojson_path = CATDataImporter.export_to_geojson(db, tier_level=1)
print(f"Data exported to {geojson_path}")

db.close()
Database Schema
CATRegion Model
id: Integer (Primary Key)
region_name: String(255)
region_code: String(50) (Unique)
tier_level: Integer
geometry: Text (GeoJSON)
population: Integer
area_sqkm: Float
access_score: Float
properties: JSON
created_at: DateTime
updated_at: DateTime
CATDataPoint Model
id: Integer (Primary Key)
region_code: String(50)
latitude: Float
longitude: Float
location_name: String(255)
access_type: String(100)
access_quality: Float
distance_km: Float
travel_time_minutes: Float
is_active: Boolean
verified: Boolean
metadata: JSON
created_at: DateTime
updated_at: DateTime
Troubleshooting
Database Lock Errors
SQLite may encounter concurrency limitations when multiple processes attempt simultaneous write operations. Ensure that only one process performs write operations at any given time. For production environments requiring higher concurrency, consider migrating to PostgreSQL with PostGIS extensions.

Import Failures
Verify that CSV and GeoJSON files conform to the specified schema requirements. Ensure all required columns and properties are present. Confirm that coordinate values are expressed in decimal degrees using the WGS84 datum.

Performance Optimization
The database includes indexes on frequently queried fields. For large datasets exceeding 100,000 records, consider implementing additional spatial indexes. Utilize pagination for queries returning large result sets to optimize performance.

Implementation Roadmap
Customize gating rules by modifying the database/init_db.py file or utilizing the API endpoints to create custom rule sets.
Import production data by preparing CSV or GeoJSON files according to the format specifications outlined in this guide.
Develop frontend interface by connecting to the provided API endpoints for data visualization and user interaction.
Implement authentication by integrating with existing authentication systems to control access and permissions.
Scale to production database by migrating to PostgreSQL with PostGIS when ready to deploy to production environments.

Additional Resources
API documentation is available at: GET /api/cat/statistics
Sample data files are located in: backend/data/samples/
Database model definitions are found in: backend/database/models.py

License
This component is part of the TENeT project. Please refer to the main LICENSE file for licensing information.
Compress this readme file and remove all the unnecesaary things
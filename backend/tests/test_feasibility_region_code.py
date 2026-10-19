# test_feasibility_endpoint.py
import pytest
from flask import json
from app import app
from database.models import CATDataPoint
from database.models import CATRegion
from database.models import CATGatingRule, CATUpload
from database.config import SessionLocal

@pytest.fixture
def client():

    """create a Flask test client here """

    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def db_session():

    """create a database session for testing heree"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


class TestFeasibilityEndpoint:
    
    def test_feasible_region(self, client, db_session):
        """Test that a region passing all rules returns FEASIBLE"""

        # Create an upload record first
        upload = CATUpload(
            filename='test_upload.csv',
            file_type='csv',
            status='completed',
            records_processed=1,
            uploaded_by='test'
        )
        db_session.add(upload)
        db_session.flush()  # This assigns an ID to upload 

        # create a region with good metrics
        region = CATRegion(
            region_code='AK-TEST',
            region_name='Test Community',
            tier_level = 1
        )
        db_session.add(region)
        db_session.flush()
        
        data_point = CATDataPoint(
            upload_id = upload.id,
            region_id = region.id,
            region_code = 'AK-TEST',
            latitude = 61.2181,
            longitude = -149.9003,
            access_quality = 75.0,
            distance_km = 30.0,
            travel_time_minutes = 45,
            access_type = 'healthcare',
            throughput_mbps = 50.0,
            latency_ms = 25.0,
            is_active = True
        )

        rule = CATGatingRule(
            rule_name = 'Tier 1 Rules',
            tier_level = 1,
            min_access_score = 60.0,
            max_distance_km = 50.0,
            max_travel_time = 60.0,
            access_types = ['healthcare'],
            is_active = True,
            priority = 1
        )

        db_session.add(rule)
        db_session.add(data_point)
        db_session.commit()
        
        # calling   the endpoint
        response = client.get('/api/cat/feasibility/AK-TEST')
        data = json.loads(response.data)
        
        
        assert response.status_code == 200
        assert data['feasible'] == True
        assert data['decision'] == 'FEASIBLE'
        assert data['region_code'] == 'AK-TEST'
        assert data['region_name'] == 'Test Community'
        
    def test_not_feasible_region(self, client, db_session):

        """Test that a region failing rules returns NOT_FEASIBLE"""

        # Create an upload record first
        upload = CATUpload(
                filename='test_upload.csv',
                file_type='csv',
                status='completed',
                records_processed=1,
                uploaded_by='test'
            )
        db_session.add(upload)
        db_session.flush()  # again this assigns id to upload

        # create a region with poor metrics
        region = CATRegion(
            region_code='AK-POOR',
            region_name='Poor Community',
            tier_level=1
        )
        db_session.add(region)
        db_session.flush()
        
        data_point = CATDataPoint(
            upload_id=upload.id,
            region_id=region.id,
            region_code='AK-POOR',
            latitude=60.7922,
            longitude=-161.7558,
            access_quality=25.0,
            distance_km=30.0,
            travel_time_minutes=45,
            access_type='healthcare',
            is_active=True
        )
        db_session.add(data_point)
        
        # just add gating rules
        rule = CATGatingRule(
            rule_name='Tier 1 Rules',
            tier_level=1,
            min_access_score=60.0,
            max_distance_km=50.0,
            max_travel_time=60.0,
            access_types=['healthcare'],
            is_active=True,
            priority=1
        )
        db_session.add(rule)
        db_session.commit()
        
        
        response = client.get('/api/cat/feasibility/AK-POOR')
        data = json.loads(response.data)
        
        
        assert response.status_code == 200
        assert data['feasible'] == False
        assert data['decision'] == 'NOT_FEASIBLE'
        assert data['failed_gate'] is not None
        assert 'Access quality 25.0 below minimum 60.0' in data['explanation']
        
    def test_no_data_point(self, client, db_session):
        """Test that a region with no data returns INSUFFICIENT_DATA"""

        # create region without datapoint here
        region = CATRegion(
            region_code='AK-NODATA',
            region_name='No Data Community',
            tier_level = 1
        )
        db_session.add(region)
        db_session.commit()
        
        
        response = client.get('/api/cat/feasibility/AK-NODATA')
        data = json.loads(response.data)
        
        
        assert response.status_code == 200
        assert data['feasible'] == False
        assert data['decision'] == 'INSUFFICIENT_DATA'
        assert 'No connectivity data available' in data['explanation']
        
    def test_region_not_found(self, client):

        """Test that a non-existent region returns 404"""
        
        response = client.get('/api/cat/feasibility/AK-NONEXISTENT')
        
    
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['error']



    def test_cat4_region_feasibility(self, client, db_session):
        """Test that CAT-4 regions use the mode-aware telehealth check, not standard gating"""


        # Create an upload record first
        upload = CATUpload(
            filename='test_upload.csv',
            file_type='csv',
            status='completed',
            records_processed=1,
            uploaded_by='test'
        )
        
        db_session.add(upload)
        db_session.flush()  # this again assigns an ID to upload


        region = CATRegion(
            region_code='AK-REMOTE',
            region_name='Remote Fly-in Community',
            tier_level=4
        )
        db_session.add(region)
        db_session.flush()

        data_point = CATDataPoint(
            upload_id=upload.id,
            region_id=region.id,
            region_code='AK-REMOTE',
            latitude=64.5011,
            longitude=-165.4064,
            access_quality=50.0,
            throughput_mbps=5.0,
            latency_ms=200.0,
            access_type='telehealth',
            is_active=True
        )
        db_session.add(data_point)
        db_session.commit()

        response = client.get('/api/cat/feasibility/AK-REMOTE?telehealth_mode=video')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['cat_tier'] == 4
        assert 'mode_results' in data  # only present on the CAT-4 branch


    def test_missing_distance_and_travel_time(self, client, db_session):
        """
        Documents current fail-open behavior: a data point with missing
        distance_km/travel_time_minutes still reports FEASIBLE, since
        check_access_gating() skips checks it can't evaluate rather than
        failing them
        """
        upload = CATUpload(
            filename='test_upload.csv', file_type='csv',
            status='completed', records_processed=1, uploaded_by='test'
        )
        db_session.add(upload)
        db_session.flush()

        region = CATRegion(
            region_code='AK-MISSING', region_name='Missing Data Community',
            tier_level=1
        )
        db_session.add(region)
        db_session.flush()

        data_point = CATDataPoint(
            upload_id=upload.id,
            region_id=region.id,
            region_code='AK-MISSING',
            latitude=61.0, longitude=-149.0,
            access_quality=75.0,
            distance_km=None,           # missing
            travel_time_minutes=None,   # missing
            access_type='healthcare',
            is_active=True
        )
        rule = CATGatingRule(
            rule_name='Tier 1 Rules', tier_level=1,
            min_access_score=60.0, max_distance_km=50.0,
            max_travel_time=60.0, access_types=['healthcare'],
            is_active=True, priority=1
        )
        db_session.add(rule)
        db_session.add(data_point)
        db_session.commit()

        response = client.get('/api/cat/feasibility/AK-MISSING')
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data['feasible'] == True  # current (possibly unintended) behavior
        assert data['decision'] == 'FEASIBLE'
import requests
import os
import zipfile
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from dotenv import load_dotenv
from location.models import HealthCenterData,InternetData
import json
from metadata.views import updateMetadata,getLastupdate
load_dotenv()
BASE_FOLDER = os.path.join(os.path.dirname(os.getcwd()),"alaska_all_data")
url = "https://healthsites.io/api/v3/facilities/"
FCCurl = "https://bdc.fcc.gov/api/public/map"
headers = {
    "username": os.environ.get("FCC_USERNAME"),
    "hash_value": os.environ.get("FCC_API")
}

params = {
    "api-key": os.environ.get("HEALTHSITE_API"),
    "page": 1,
    "extent": "-179.15, 51.21, -129.97, 71.44",
}

def load_data(latest_date):
    try:
        res = requests.get(  
            f"{FCCurl}/downloads/listAvailabilityData/{latest_date}",
            headers=headers)
        results = res.json()
        updateMetadata(latest_date)
        data = results.get("data")
        alaskaData = [item for item in data if item["state_name"] == "Alaska"]
        oneData = alaskaData[0]
        fileID = oneData["file_id"]
        DownloadUrl = f"{FCCurl}/downloads/downloadFile/availability/{fileID}/1"
        res = requests.get(url=DownloadUrl,headers=headers)
        os.makedirs(BASE_FOLDER, exist_ok=True)
        zip_path = os.path.join(BASE_FOLDER, "alaska.zip")
        extract_path = os.path.join(BASE_FOLDER, f"alaska_data_{fileID}")
        with open(zip_path, "wb") as f:
            f.write(res.content)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
    except Exception as e:
        print(f"the error is {e}")
    
def updateHealthData():
    try:
        result = requests.get(url, params=params)
        datas = result.json()
        for data in datas:
            HealthCenterData.objects.update_or_create(
                name=(data.get("attributes")).get("name"),
                location=Point(data.get("centroid").get("coordinates")[1], data.get("centroid").get("coordinates")[0]) 
            )
    except Exception as e:
        print(f"the error is {e}")

def updaateInternetData():
    try:
        result = requests.get(url=f"{FCCurl}/listAsOfDates",headers=headers)
        dates = result.json()["data"]
        latest_date = max(d["as_of_date"] for d in dates if d["data_type"] == "availability")
        if not getLastupdate() or latest_date != getLastupdate() :
            print("updating")
            load_data(latest_date)
            data_mapping = {
                'frn': 'frn',
                'providerid': 'providerid',
                'brandname': 'brandname',
                'technology': 'technology',
                'mindown': 'mindown',
                'minup': 'minup',
                'minsignal': 'minsignal',
                'environmnt': 'environmnt',
                'h3_res9_id': 'h3_res9_id',
                'mpoly': 'POLYGON', 
            }
            for folder in os.listdir(BASE_FOLDER):
                folder_path = os.path.join(BASE_FOLDER, folder)
                if os.path.isdir(folder_path):
                    for file in os.listdir(folder_path):
                        full_path = os.path.join(folder_path, file)
                        if file.endswith(".shp"):
                            lm = LayerMapping(InternetData, full_path, data_mapping,
                                transform=False)
                            lm.save(fid_range=(0, 100000), strict=False, verbose=False)
        else:
            print("no update")
    except Exception as e:
        print(f"error is {e}")

def get_health_data():
    updateHealthData()
    try:
        HealthDatas = HealthCenterData.objects.all()
        data = []
        for HealthData in HealthDatas:
            data.append({"name":HealthData.name,"lat":HealthData.location.y,"lon":HealthData.location.x})
        return data
    except Exception as e:
        print(f"the error is {e}")

def get_internet_data():
    updaateInternetData()
    queryset = InternetData.objects.all()[:50000]
    features = []
    for item in queryset:
        geom = json.loads(item.mpoly.json) if item.mpoly else None
        feature = {
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "brandname": item.brandname,
                "technology": item.technology,
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }
    
def calculateScore(lat,lng,radius):
    search_location = Point(float(lng), float(lat), srid=4326)
    test_location = Point(float(lat), float(lng), srid=4326)
    targetDown = 25
    targetUp = 5
    weight = [0.35,0.35,0.3]
    try:
        result = {}
        obj = InternetData.objects.filter(mpoly__contains = test_location).first()
        score = 0
        if obj != None:
            score+= weight[0]*min(1,obj.minup/targetUp)
            print(obj.mindown,obj.minup)
            score+= weight[1]*min(1,obj.mindown/targetDown)
            print(score)
        closestHealthCenter = HealthCenterData.objects.filter(name__isnull = False).annotate(distance=Distance('location', search_location, spheroid=True)).order_by('distance').first()
        if closestHealthCenter:
            result["closestHospital"] = closestHealthCenter.name
            result["distanceToHospital"] = (closestHealthCenter.distance.m)/1000
            score+=weight[2]*min(1,((closestHealthCenter.distance.m)/1000)/radius)
        score *= 100
        result["score"] = round(score,2)
        print(score)
        return result
    except Exception as e:
        print(e)
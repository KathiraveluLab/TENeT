import requests
import os
import zipfile
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from dotenv import load_dotenv
import h3
# from metadata.views import updateMetadata,getLastupdate
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
# def load_data():
#     try:
#         print("loading data")
#         result = requests.get(url=f"{FCCurl}/listAsOfDates",headers=headers)
#         dates = result.json()["data"]
#         latest_date = max(d["as_of_date"] for d in dates if d["data_type"] == "availability")
#         if not getLastupdate() or latest_date != getLastupdate() :
#             res = requests.get(  
#                 f"{FCCurl}/downloads/listAvailabilityData/{latest_date}",
#                 headers=headers)
#             results = res.json()
#             updateMetadata(latest_date)
#             data = results.get("data")
#             alaskaData = [item for item in data if item["state_name"] == "Alaska"]
#             oneData = alaskaData[0]
#             fileID = oneData["file_id"]
#             DownloadUrl = f"{FCCurl}/downloads/downloadFile/availability/{fileID}/1"
#             res = requests.get(url=DownloadUrl,headers=headers)
#             os.makedirs(BASE_FOLDER, exist_ok=True)
#             zip_path = os.path.join(BASE_FOLDER, "alaska.zip")
#             extract_path = os.path.join(BASE_FOLDER, f"alaska_data_{fileID}")
#             with open(zip_path, "wb") as f:
#                 f.write(res.content)
#             with zipfile.ZipFile(zip_path, "r") as zip_ref:
#                 zip_ref.extractall(extract_path)
#         else:
#             print("no update")
#     except Exception as e:
#         print(f"the error is {e}")
    
def get_health_data():
    try:
        print("health started")
        result = requests.get(url, params=params)
        data = result.json()
        healthData = [{"lat":item.get("centroid").get("coordinates")[1], "lon":item.get("centroid").get("coordinates")[0],"name":(item.get("attributes")).get("name")} for item in data]
        print("done health")
        return healthData
    except Exception as e:
        print(f"the error is {e}")


# def get_internet_data():
#     load_data()
#     all_geometries = []
#     for folder in os.listdir(BASE_FOLDER):
#         folder_path = os.path.join(BASE_FOLDER, folder)
#         if os.path.isdir(folder_path):
#             for fil in os.listdir(folder_path):
#                 if fil.endswith(".shp"):
#                     file_path = os.path.join(folder_path, fil)
#                     gdf = gpd.read_file(file_path)
#                     gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.001, preserve_topology=True)
#                     all_geometries.extend(gdf.geometry)
#     print("done internet")
#     return gpd.GeoDataFrame(geometry=all_geometries, crs="EPSG:4326").__geo_interface__
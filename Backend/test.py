import requests
import os
import zipfile
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

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
   
try:
    result = requests.get(url=f"{FCCurl}/listAsOfDates",headers=headers)
    dates = result.json()["data"]
    latest_date = max(d["as_of_date"] for d in dates if d["data_type"] == "availability")
    res = requests.get(
        f"{FCCurl}/downloads/listAvailabilityData/{latest_date}",
        headers=headers
    )
    results = res.json()
    data = results["data"]
    alaskaData = [item for item in data if item["state_name"] == "Alaska"]
    result = requests.get(url, params=params)
    data = result.json()
    pointData = [[item["centroid"]["coordinates"]] for item in data]
    points_gdf = gpd.GeoDataFrame(
    [{'geometry': Point(p)} for p in pointData],
    crs="EPSG:4326" )
    points_gdf = points_gdf.to_crs(epsg=3857)
    # for i in alaskaData:
    #     fileID = i["file_id"]
    #     DownloadUrl = f"{FCCurl}/downloads/downloadFile/availability/{fileID}/1"
    #     res = requests.get(url=DownloadUrl,headers=headers)
    #     with open("alaska.zip", "wb") as f:
    #         f.write(res.content)
    #     with zipfile.ZipFile("alaska.zip", "r") as zip_ref:
    #         zip_ref.extractall("alaska_data")
    base_folder = "alaska_all_data"
    os.makedirs(base_folder, exist_ok=True)

    # ------------------------------
    # Download and extract data
    # ------------------------------
    # for i in alaskaData:
    #     fileID = i["file_id"]
        
    #     zip_filename = os.path.join(base_folder, f"alaska_{fileID}.zip")
    #     extract_folder = os.path.join(base_folder, f"alaska_data_{fileID}")
        
    #     # Download zip if not already exists
    #     if not os.path.exists(zip_filename):
    #         DownloadUrl = f"{FCCurl}/downloads/downloadFile/availability/{fileID}/1"
    #         print(f"Downloading {zip_filename} ...")
    #         res = requests.get(url=DownloadUrl, headers=headers)
    #         with open(zip_filename, "wb") as f:
    #             f.write(res.content)
        
    #     # Extract if folder doesn't exist
    #     if not os.path.exists(extract_folder):
    #         print(f"Extracting {zip_filename} ...")
    #         with zipfile.ZipFile(zip_filename, "r") as zip_ref:
    #             zip_ref.extractall(extract_folder)

    # ------------------------------
    # Read all shapefiles into one GeoDataFrame
    # ------------------------------
    all_gdfs = []
    for folder in os.listdir(base_folder):
        folder_path = os.path.join(base_folder, folder)
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith(".shp"):
                    shp_path = os.path.join(folder_path, file)
                    gdf = gpd.read_file(shp_path)
                    all_gdfs.append(gdf)
                    
    if all_gdfs:
        coverage_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True))
        coverage_gdf = coverage_gdf.to_crs(epsg=3857)  
    else:
        raise ValueError("No shapefiles found!")
    fig, ax = plt.subplots(figsize=(12,12))
    points_gdf.plot(ax=ax, color='red', markersize=50, marker='o', label='Clinics')
    coverage_gdf.plot(ax=ax, alpha=0.5, edgecolor='blue', facecolor='cyan', label='Coverage')

    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)

    ax.set_axis_off()
    plt.legend()
    plt.show()
except Exception as e:
    print(f"the error is {e}")
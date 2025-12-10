import requests

OSRM_URL = "http://router.project-osrm.org"

def get_transport_score(lat: float, lon: float):
    # Nearest road via OSRM
    nearest = requests.get(
        f"{OSRM_URL}/nearest/v1/driving/{lon},{lat}"
    ).json()

    if "waypoints" not in nearest:
        return {"error": "No transport data available"}

    node = nearest["waypoints"][0]

    return {
        "nearest_road_distance": node.get("distance"),
        "nearest_road_location": node.get("location"),
        "transport_score": 1 / (1 + node.get("distance", 1000))
    }
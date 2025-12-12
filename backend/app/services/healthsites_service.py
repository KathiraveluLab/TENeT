import requests
from app.clients.nppes_client import query_nppes

ALASKA_ZIP_PREFIXES = ["995", "996", "997", "998", "999"]

def fetch_healthsites(state: str = None, city: str = None):
    # primary query
    primary_results = query_nppes(state=state, city=city)

    # Alaska fallback logic
    if state and state.upper() == "AK" and len(primary_results) == 0:
        zip_relaxed_results = []
        for prefix in ALASKA_ZIP_PREFIXES:
            zip_relaxed_results.extend(
                query_nppes(postal_code=f"{prefix}*")
            )

        combined = primary_results + zip_relaxed_results
        deduped = {item["npi"]: item for item in combined}.values()

        return {
            "count": len(deduped),
            "data": list(deduped),
            "fallback_used": True
        }

    return {
        "count": len(primary_results),
        "data": primary_results,
        "fallback_used": False,
    }

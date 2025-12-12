import requests
from app.clients.nppes_client import query_nppes

ALASKA_ZIP_PREFIXES = ["995", "996", "997", "998", "999"]

def fetch_specialists(taxonomy: str = None, state: str = None, city: str = None):

    primary_results = query_nppes(
        taxonomy_description=taxonomy,
        state=state,
        city=city
    )

    if state and state.upper() == "AK" and len(primary_results) == 0:

        # Alaska fallback #1: taxonomy + ZIP prefixes
        zip_results = []
        for prefix in ALASKA_ZIP_PREFIXES:
            zip_results.extend(
                query_nppes(
                    taxonomy_description=taxonomy,
                    postal_code=f"{prefix}*"
                )
            )

        # Alaska fallback #2: ZIP prefixes without taxonomy
        zip_relaxed_results = []
        if len(zip_results) == 0:
            for prefix in ALASKA_ZIP_PREFIXES:
                zip_relaxed_results.extend(
                    query_nppes(postal_code=f"{prefix}*")
                )

        combined = primary_results + zip_results + zip_relaxed_results
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

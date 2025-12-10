import requests

NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"
ALASKA_ZIP_PREFIXES = ["995", "996", "997", "998", "999"]


def fetch_healthsites(state: str = None, city: str = None):

    # 1. normal API query
    primary_results = _query_nppes(state=state,city=city)

    if state and state.upper() == "AK" and len(primary_results) == 0:
        
        zip_relaxed_results = []
        for prefix in ALASKA_ZIP_PREFIXES:
            zip_relaxed_results.extend(
                _query_nppes(postal_code=f"{prefix}*")
            )

        combined = primary_results  + zip_relaxed_results

        deduped = {item["npi"]: item for item in combined}.values()

        return {
            "count": len(deduped),
            "data": list(deduped),
            "fallback_used": True
        }

    # If not Alaska or enough results:
    return {
        "count": len(primary_results),
        "data": primary_results,
        "fallback_used": False
    }



def _query_nppes(**params):
    
    params.update ({
        "version": "2.1",
        "limit": 200,
    })

    try:
        response = requests.get(NPPES_API_URL, params=params)
        response.raise_for_status()
    except Exception:
        return []

    data = response.json()
    raw_results = data.get("results", [])
    processed = []

    for provider in raw_results:
        basic = provider.get("basic", {})
        addresses = provider.get("addresses", [])
        taxonomies = provider.get("taxonomies", [])
        
        practice_address = next(
            (addr for addr in addresses if addr.get("address_purpose") == "LOCATION"),
            addresses[0] if addresses else None
        ) #could use a different address other than location e.g. mailing

        processed.append({
            "npi": provider.get("number"),
            "name": (
                f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
                if basic.get("first_name") else basic.get("organization_name", "")
            ),
            "status": basic.get("status"),
            "taxonomies":  taxonomies,
            "practice_address": {
                "address": practice_address.get("address_1") if practice_address else None,
                "city": practice_address.get("city") if practice_address else None,
                "state": practice_address.get("state") if practice_address else None,
                "postal_code": practice_address.get("postal_code") if practice_address else None,
            }
        })

    return processed

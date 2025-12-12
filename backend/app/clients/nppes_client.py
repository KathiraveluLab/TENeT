# app/clients/nppes_client.py

import requests

NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"

def query_nppes(**params):

    params.update({
        "version": "2.1",
        "limit": 200,
    })

    try:
        response = requests.get(NPPES_API_URL, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"NPPES request failed: {e}")
        return []

    data = response.json()
    raw_results = data.get("results", [])
    processed = []

    for provider in raw_results:
        basic = provider.get("basic", {})
        addresses = provider.get("addresses", [])
        taxonomies = provider.get("taxonomies", [])

        # Pick LOCATION address if available, else first address
        practice_address = next(
            (addr for addr in addresses if addr.get("address_purpose") == "LOCATION"),
            addresses[0] if addresses else None
        )

        processed.append({
            "npi": provider.get("number"),
            "name": (
                f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
                if basic.get("first_name")
                else basic.get("organization_name", "")
            ),
            "status": basic.get("status"),
            "taxonomies": [
                {
                    "code": t.get("code"),
                    "desc": t.get("desc"),
                    "primary": t.get("primary"),
                }
                for t in taxonomies
            ],
            "practice_address": {
                "address": practice_address.get("address_1") if practice_address else None,
                "city": practice_address.get("city") if practice_address else None,
                "state": practice_address.get("state") if practice_address else None,
                "postal_code": practice_address.get("postal_code") if practice_address else None,
            },
        })

    return processed

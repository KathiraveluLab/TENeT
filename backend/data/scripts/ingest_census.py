#!/usr/bin/env python3
"""
Census ACS Income Data Ingestion Script

Fetches median household income (B19013_001E) and total population (B01003_001E)
for Alaska ZIP Code Tabulation Areas (ZCTAs, 995xx-999xx) from U.S. Census
Bureau American Community Survey (ACS) 5-Year Estimates.

Supports two data paths:
1. Public Census Summary File + Gazetteer + ZCTA-to-Place relationship files
   (no API key required; default when CENSUS_API_KEY / --key is omitted).
2. Census Data API v1 batched requests (when --key or CENSUS_API_KEY is set),
   enriched with Gazetteer / Place-weighted centroids.
"""

import argparse
import csv
import io
import os
import sys
import time
import zipfile
from typing import Dict, Iterable, List, Optional, Tuple

import requests

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database.config import SessionLocal, engine  # noqa: E402
from database.models import Base, CensusIncome  # noqa: E402

DEFAULT_ACS_YEAR = 2024
DEFAULT_CSV_PATH = os.path.join(
    backend_dir, "data", "processed_data", "alaska_acs_zcta_income.csv"
)
CENSUS_SUMMARY_BASE_URL = "https://www2.census.gov/programs-surveys/acs/summary_file"
CENSUS_GAZETTEER_BASE_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer"
ZCTA_PLACE_REL_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
    "tab20_zcta520_place20_natl.txt"
)
SQ_METERS_PER_SQ_MILE = 2589988.11
MIN_CONTAINED_PLACE_PART_SQMI = 0.5
CONTAINMENT_AREA_RATIO = 1.15
MIN_CONTAINED_ZCTA_THRESHOLD_SQMI = 250.0

# Known Alaska ZCTAs (comprehensive list; 995xx-999xx)
ALASKA_ZCTAS = [
    # Anchorage area
    "99501", "99502", "99503", "99504", "99505", "99506", "99507", "99508",
    "99509", "99510", "99511", "99513", "99514", "99515", "99516", "99517",
    "99518", "99519", "99520", "99521", "99522", "99523", "99524", "99529",
    "99530", "99540",
    # Mat-Su / Eagle River
    "99567", "99577", "99587", "99588",
    # Kenai Peninsula
    "99556", "99568", "99572", "99574", "99575", "99603", "99605", "99610",
    "99611", "99615", "99631", "99635", "99639", "99645", "99654", "99664",
    "99669", "99672",
    # Fairbanks / Interior
    "99701", "99702", "99703", "99704", "99705", "99706", "99707", "99708",
    "99709", "99710", "99711", "99712", "99714", "99716", "99720", "99721",
    "99722", "99723", "99724", "99725", "99726", "99727", "99729", "99730",
    "99732", "99733", "99734", "99736", "99737", "99738", "99739", "99740",
    "99741", "99742", "99743", "99744", "99745", "99746", "99747", "99748",
    "99749", "99750", "99751", "99752", "99753", "99754", "99755", "99756",
    "99757", "99758", "99759", "99760", "99761", "99762", "99763", "99764",
    "99765", "99766", "99767", "99768", "99769", "99770", "99771", "99772",
    "99773", "99774", "99775", "99776", "99777", "99778", "99780", "99781",
    "99782", "99783", "99784", "99785", "99786", "99788", "99789", "99790",
    "99791",
    # Southeast Alaska
    "99801", "99802", "99803", "99811", "99820", "99821", "99824", "99825",
    "99826", "99827", "99829", "99830", "99832", "99833", "99835", "99836",
    "99840", "99841",
    # Ketchikan / Prince of Wales
    "99901", "99903", "99918", "99919", "99921", "99922", "99923", "99925",
    "99926", "99927", "99928", "99929",
    # Western Alaska / Bethel
    "99545", "99546", "99547", "99548", "99549", "99550", "99551", "99552",
    "99553", "99554", "99555", "99557", "99558", "99559", "99561", "99563",
    "99564", "99565", "99566", "99569", "99571", "99573", "99576", "99578",
    "99579", "99580", "99581", "99583", "99585", "99586", "99589", "99590",
    "99591", "99602", "99604", "99606", "99607", "99609", "99612", "99613",
    "99614", "99620", "99621", "99622", "99624", "99625", "99626", "99627",
    "99628", "99630", "99632", "99633", "99634", "99636", "99637", "99638",
    "99640", "99641", "99643", "99644", "99647", "99648", "99649", "99650",
    "99651", "99652", "99653", "99655", "99656", "99657", "99658", "99659",
    "99660", "99661", "99662", "99663", "99665", "99666", "99667", "99668",
    "99670", "99671", "99674", "99675", "99676", "99677", "99678", "99679",
    "99680", "99681", "99682", "99683", "99684", "99685", "99686", "99687",
    "99688", "99689", "99690", "99691", "99692", "99693", "99694", "99695",
]

# Curated urban/hub ZCTA centroids used where multi-polygon or remote-parcel ZCTAs
# (e.g. 99503 Anchorage, 99701 Fairbanks) pull Census Gazetteer internal points
# hundreds of km away from the primary urban community.
ZCTA_CENTROIDS = {
    "99501": (61.2181, -149.9003),
    "99502": (61.1508, -149.9294),
    "99503": (61.1875, -149.8697),
    "99504": (61.2040, -149.7400),
    "99505": (61.2628, -149.6525),
    "99506": (61.2567, -149.8086),
    "99507": (61.1425, -149.8125),
    "99508": (61.2036, -149.8139),
    "99515": (61.1089, -149.8639),
    "99516": (61.0847, -149.7789),
    "99517": (61.1947, -149.9500),
    "99518": (61.1525, -149.9125),
    "99540": (60.9458, -149.1583),
    "99556": (59.6425, -151.5100),
    "99559": (60.7922, -161.7558),
    "99577": (61.2308, -149.4489),
    "99587": (60.9658, -148.8766),  # Girdwood (Gazetteer internal point; fixes legacy typo)
    "99611": (60.5528, -151.2581),
    "99615": (57.7900, -152.4072),
    "99654": (61.5811, -149.4389),
    "99669": (60.5400, -151.2739),
    "99676": (62.3236, -150.1089),
    "99686": (61.1308, -146.3483),
    "99701": (64.8378, -147.7164),
    "99705": (64.8503, -147.8283),
    "99709": (64.8572, -147.8258),
    "99712": (64.9500, -147.4000),
    "99723": (71.2906, -156.7886),
    "99741": (64.7414, -156.8734),  # Galena (Gazetteer internal point; fixes legacy Nenana mix-up)
    "99762": (64.5011, -165.4064),
    "99801": (58.3019, -134.4197),
    "99824": (58.3800, -134.6400),
    "99827": (59.4519, -135.9319),
    "99833": (56.8119, -132.9536),
    "99835": (57.0531, -135.3350),
    "99901": (55.3422, -131.6461),
}

_ALASKA_ZCTA_PREFIXES = ("995", "996", "997", "998", "999")
_ZCTA_GEOID_PREFIX = "860Z200US"


def is_alaska_zcta(zcta: str) -> bool:
    """Return True if a 5-digit ZCTA code falls inside Alaska (995xx-999xx)."""
    return len(zcta) == 5 and zcta.isdigit() and zcta[:3] in _ALASKA_ZCTA_PREFIXES


def parse_acs_positive_float(raw_value: object) -> Optional[float]:
    """Parse an ACS numeric field, returning None for missing/suppressed sentinels."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text or text in {".", "-", "null", "None"}:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def parse_acs_nonnegative_int(raw_value: object) -> Optional[int]:
    """Parse a non-negative integer ACS estimate, returning None for suppressed values."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text or text in {".", "-", "null", "None"}:
        return None
    try:
        parsed = int(float(text))
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def parse_zcta_gazetteer(tsv_stream: Iterable[str]) -> Dict[str, Tuple[float, float, float]]:
    """Parse tab-delimited Census ZCTA Gazetteer rows for Alaska ZCTAs -> (lat, lon, aland_sqmi)."""
    out: Dict[str, Tuple[float, float, float]] = {}
    reader = csv.DictReader(tsv_stream, delimiter="\t")
    for row in reader:
        cleaned = {k.strip(): v.strip() for k, v in row.items() if k}
        zcta = cleaned.get("GEOID", "")
        if is_alaska_zcta(zcta):
            out[zcta] = (
                float(cleaned["INTPTLAT"]),
                float(cleaned["INTPTLONG"]),
                float(cleaned["ALAND_SQMI"]),
            )
    return out


def parse_place_gazetteer(tsv_stream: Iterable[str]) -> Dict[str, Tuple[str, float, float, float]]:
    """Parse tab-delimited Census Place Gazetteer rows for Alaska -> (name, lat, lon, aland_sqmi)."""
    out: Dict[str, Tuple[str, float, float, float]] = {}
    reader = csv.DictReader(tsv_stream, delimiter="\t")
    for row in reader:
        cleaned = {k.strip(): v.strip() for k, v in row.items() if k}
        if cleaned.get("USPS") == "AK" and cleaned.get("GEOID"):
            out[cleaned["GEOID"]] = (
                cleaned["NAME"],
                float(cleaned["INTPTLAT"]),
                float(cleaned["INTPTLONG"]),
                float(cleaned["ALAND_SQMI"]),
            )
    return out


def parse_acs_dat_stream(
    lines: Iterable[str],
    estimate_col: str,
) -> Tuple[Dict[str, Optional[str]], Dict[str, Optional[str]]]:
    """Stream a pipe-delimited ACS Summary File .dat file and extract AK ZCTA and Place estimates."""
    zcta_raw: Dict[str, Optional[str]] = {}
    place_raw: Dict[str, Optional[str]] = {}
    reader = csv.DictReader(lines, delimiter="|")
    for row in reader:
        geoid = (row.get("GEO_ID") or "").strip()
        if geoid.startswith(_ZCTA_GEOID_PREFIX):
            zcta = geoid[len(_ZCTA_GEOID_PREFIX):]
            if is_alaska_zcta(zcta):
                zcta_raw[zcta] = row.get(estimate_col)
        elif geoid.startswith("160") and "US02" in geoid:
            place_geoid = geoid.split("US", 1)[1]
            place_raw[place_geoid] = row.get(estimate_col)
    return zcta_raw, place_raw


def parse_zcta_place_rel_stream(
    lines: Iterable[str],
    ak_places: Dict[str, Tuple[str, float, float, float]],
) -> Dict[str, List[Tuple[str, float, float]]]:
    """Parse Census 2020 ZCTA-to-Place relationship rows -> {zcta: [(place_geoid, part_sqmi, zcta_sqmi)]}."""
    links: Dict[str, List[Tuple[str, float, float]]] = {}
    reader = csv.DictReader(lines, delimiter="|")
    for row in reader:
        zcta = (row.get("GEOID_ZCTA5_20") or "").strip()
        place_geoid = (row.get("GEOID_PLACE_20") or "").strip()
        if not is_alaska_zcta(zcta) or place_geoid not in ak_places:
            continue
        zcta_sqmi = int(row.get("AREALAND_ZCTA5_20") or 0) / SQ_METERS_PER_SQ_MILE
        part_sqmi = int(row.get("AREALAND_PART") or 0) / SQ_METERS_PER_SQ_MILE
        links.setdefault(zcta, []).append((place_geoid, part_sqmi, zcta_sqmi))
    return links


def resolve_zcta_centroid(
    zcta: str,
    gaz_zctas: Dict[str, Tuple[float, float, float]],
    ak_places: Optional[Dict[str, Tuple[str, float, float, float]]] = None,
    place_pops: Optional[Dict[str, Optional[int]]] = None,
    zcta_place_links: Optional[Dict[str, List[Tuple[str, float, float]]]] = None,
) -> Optional[Tuple[float, float, str]]:
    """
    Resolve an authoritative representative coordinate for an Alaska ZCTA.

    Priority:
    1. Curated urban/multi-polygon hub centroid in ZCTA_CENTROIDS
    2. Population-weighted centroid of non-consolidated Census Places contained in the ZCTA
       (eliminates tundra internal-point drift in large rural ZCTAs such as 99574/99752)
    3. Official Census ZCTA Gazetteer internal point (INTPTLAT, INTPTLONG)
    """
    if zcta in ZCTA_CENTROIDS:
        lat, lon = ZCTA_CENTROIDS[zcta]
        return lat, lon, "curated_hub"

    gaz_entry = gaz_zctas.get(zcta)
    if ak_places and place_pops and zcta_place_links and zcta in zcta_place_links:
        contained: List[Tuple[float, float, int]] = []
        for place_geoid, part_sqmi, zcta_sqmi in zcta_place_links[zcta]:
            place = ak_places.get(place_geoid)
            pop = place_pops.get(place_geoid) or 0
            if not place or pop <= 0 or part_sqmi < MIN_CONTAINED_PLACE_PART_SQMI:
                continue
            _, plat, plon, place_sqmi = place
            # Skip consolidated municipalities (e.g. Anchorage/Juneau/Sitka boroughs) that
            # enclose many small ZCTAs so distinct urban ZIP centroids never collapse.
            if place_sqmi <= max(zcta_sqmi * CONTAINMENT_AREA_RATIO, MIN_CONTAINED_ZCTA_THRESHOLD_SQMI):
                contained.append((plat, plon, pop))
        if contained:
            total_pop = sum(pop for _, _, pop in contained)
            w_lat = sum(plat * pop for plat, _, pop in contained) / total_pop
            w_lon = sum(plon * pop for _, plon, pop in contained) / total_pop
            return w_lat, w_lon, "place_pop_weighted"

    if gaz_entry is not None:
        return gaz_entry[0], gaz_entry[1], "census_gazetteer"
    return None


def _read_url_or_cache(
    url: str,
    cache_dir: Optional[str],
    filename: str,
    timeout: int = 90,
) -> bytes:
    """Fetch binary content from cache_dir if present, otherwise download from url."""
    if cache_dir:
        cached = os.path.join(cache_dir, filename)
        if os.path.exists(cached):
            with open(cached, "rb") as fh:
                return fh.read()
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    content = response.content
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, filename), "wb") as fh:
            fh.write(content)
    return content


def _load_gazetteer_payload(year: int, kind: str, cache_dir: Optional[str]) -> bytes:
    """Load Census ZCTA or Place Gazetteer zip bytes, falling back to 2024 if year file absent."""
    for candidate_year in (year, 2024):
        filename = f"{candidate_year}_Gaz_{kind}_national.zip"
        url = f"{CENSUS_GAZETTEER_BASE_URL}/{candidate_year}_Gazetteer/{filename}"
        try:
            return _read_url_or_cache(url, cache_dir, filename, timeout=60)
        except requests.HTTPError:
            if candidate_year == 2024:
                raise
    raise RuntimeError(f"Unable to download {kind} Gazetteer for ACS year {year}")


def _stream_zcta_place_links(
    ak_places: Dict[str, Tuple[str, float, float, float]],
    cache_dir: Optional[str],
) -> Dict[str, List[Tuple[str, float, float]]]:
    """Stream national 2020 ZCTA-to-Place relationship file and retain only Alaska rows."""
    if cache_dir:
        ak_cache = os.path.join(cache_dir, "tab20_zcta520_place20_ak.txt")
        if os.path.exists(ak_cache):
            with open(ak_cache, "r", encoding="utf-8-sig") as fh:
                return parse_zcta_place_rel_stream(fh, ak_places)

    with requests.get(ZCTA_PLACE_REL_URL, stream=True, timeout=90) as response:
        response.raise_for_status()
        lines = response.iter_lines(decode_unicode=True)
        header = next(lines)
        ak_lines = [header]
        for line in lines:
            if line and line.split("|", 3)[1][:3] in _ALASKA_ZCTA_PREFIXES:
                ak_lines.append(line)

    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "tab20_zcta520_place20_ak.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(ak_lines))
    return parse_zcta_place_rel_stream(ak_lines, ak_places)


def load_alaska_geography(
    year: int = DEFAULT_ACS_YEAR,
    place_pops: Optional[Dict[str, Optional[int]]] = None,
    cache_dir: Optional[str] = None,
) -> Tuple[
    Dict[str, Tuple[float, float, float]],
    Dict[str, Tuple[str, float, float, float]],
    Dict[str, List[Tuple[str, float, float]]],
]:
    """Load Census ZCTA Gazetteer, Alaska Place Gazetteer, and ZCTA-Place intersections."""
    zcta_zip_bytes = _load_gazetteer_payload(year, "zcta", cache_dir)
    place_zip_bytes = _load_gazetteer_payload(year, "place", cache_dir)

    with zipfile.ZipFile(io.BytesIO(zcta_zip_bytes)) as zf:
        with zf.open(zf.namelist()[0]) as member:
            gaz_zctas = parse_zcta_gazetteer(io.TextIOWrapper(member, encoding="utf-8"))

    with zipfile.ZipFile(io.BytesIO(place_zip_bytes)) as zf:
        with zf.open(zf.namelist()[0]) as member:
            ak_places = parse_place_gazetteer(io.TextIOWrapper(member, encoding="utf-8"))

    zcta_place_links = _stream_zcta_place_links(ak_places, cache_dir) if place_pops else {}
    return gaz_zctas, ak_places, zcta_place_links


def fetch_bulk_alaska_income(
    year: int = DEFAULT_ACS_YEAR,
    cache_dir: Optional[str] = None,
) -> List[Dict]:
    """
    Fetch statewide Alaska ACS 5-Year ZCTA income (B19013_001E) and population (B01003_001E)
    from U.S. Census public Summary File mirrors without requiring an API key.
    """
    print(f"[INFO] Fetching ACS {year} 5-Year Summary File tables (B19013, B01003)...")
    b19013_bytes = _read_url_or_cache(
        f"{CENSUS_SUMMARY_BASE_URL}/{year}/table-based-SF/data/5YRData/acsdt5y{year}-b19013.dat",
        cache_dir,
        f"acsdt5y{year}-b19013.dat",
    )
    b01003_bytes = _read_url_or_cache(
        f"{CENSUS_SUMMARY_BASE_URL}/{year}/table-based-SF/data/5YRData/acsdt5y{year}-b01003.dat",
        cache_dir,
        f"acsdt5y{year}-b01003.dat",
    )

    zcta_inc_raw, _ = parse_acs_dat_stream(
        io.StringIO(b19013_bytes.decode("utf-8")), "B19013_E001"
    )
    zcta_pop_raw, place_pop_raw = parse_acs_dat_stream(
        io.StringIO(b01003_bytes.decode("utf-8")), "B01003_E001"
    )
    place_pops = {
        geoid: parse_acs_nonnegative_int(val) for geoid, val in place_pop_raw.items()
    }

    print(f"[INFO] Resolving Census ZCTA Gazetteer & ZCTA-Place centroids ({year})...")
    gaz_zctas, ak_places, zcta_place_links = load_alaska_geography(
        year=year, place_pops=place_pops, cache_dir=cache_dir
    )

    data_source = (
        f"US Census ACS {year} 5-Year (B19013/B01003) + Gazetteer/Place Centroids"
    )
    records: List[Dict] = []
    suppressed_count = 0
    for zcta in sorted(gaz_zctas):
        median_income = parse_acs_positive_float(zcta_inc_raw.get(zcta))
        if median_income is None:
            suppressed_count += 1
            continue

        resolved = resolve_zcta_centroid(
            zcta, gaz_zctas, ak_places=ak_places,
            place_pops=place_pops, zcta_place_links=zcta_place_links,
        )
        if resolved is None:
            continue
        lat, lon, centroid_method = resolved
        population = parse_acs_nonnegative_int(zcta_pop_raw.get(zcta))
        records.append({
            "zcta": zcta,
            "name": f"ZCTA5 {zcta}",
            "median_income": median_income,
            "population": population,
            "centroid_lat": round(lat, 6),
            "centroid_lon": round(lon, 6),
            "acs_year": year,
            "centroid_method": centroid_method,
            "data_source": data_source,
        })

    print(
        f"[SUCCESS] Retrieved {len(records)} published Alaska ZCTAs "
        f"({suppressed_count} Census-suppressed/missing omitted out of {len(gaz_zctas)} in Gazetteer)"
    )
    return records


def fetch_zcta_batch(
    zctas: List[str],
    api_key: str,
    year: int = DEFAULT_ACS_YEAR,
) -> List[Dict]:
    """Fetch B19013/B01003 income and population for a batch of ZCTAs via the Census API."""
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    zcta_list = ",".join(zctas)
    params = {
        "get": "NAME,B19013_001E,B01003_001E",
        "for": f"zip code tabulation area:{zcta_list}",
        "key": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            return []

        data = response.json()
        if not data or len(data) < 2:
            return []

        headers = data[0]
        records: List[Dict] = []
        for row in data[1:]:
            record = dict(zip(headers, row))
            income = parse_acs_positive_float(record.get("B19013_001E"))
            if income is None:
                continue
            zcta = str(record.get("zip code tabulation area", "")).strip()
            if not is_alaska_zcta(zcta):
                continue
            records.append({
                "zcta": zcta,
                "name": record.get("NAME", ""),
                "median_income": income,
                "population": parse_acs_nonnegative_int(record.get("B01003_001E")),
                "acs_year": year,
                "data_source": f"US Census ACS {year} 5-Year API (B19013/B01003)",
            })
        return records
    except Exception as exc:
        print(f"  Error: {exc}")
        return []


def fetch_all_alaska_income(
    api_key: str,
    year: int = DEFAULT_ACS_YEAR,
    cache_dir: Optional[str] = None,
) -> List[Dict]:
    """Fetch income data for Alaska ZCTAs via Census API and enrich with Gazetteer centroids."""
    print(f"[INFO] Fetching Census ACS {year} income data via API...")
    gaz_zctas, ak_places, _ = load_alaska_geography(year=year, cache_dir=cache_dir)
    all_zctas = sorted(set(ALASKA_ZCTAS) | set(gaz_zctas))

    all_records: List[Dict] = []
    batch_size = 50
    for i in range(0, len(all_zctas), batch_size):
        batch = all_zctas[i:i + batch_size]
        print(f"  Fetching batch {i // batch_size + 1}... ({len(batch)} ZCTAs)")
        records = fetch_zcta_batch(batch, api_key, year=year)
        for rec in records:
            resolved = resolve_zcta_centroid(rec["zcta"], gaz_zctas, ak_places=ak_places)
            if resolved is not None:
                rec["centroid_lat"] = round(resolved[0], 6)
                rec["centroid_lon"] = round(resolved[1], 6)
                rec["centroid_method"] = resolved[2]
        all_records.extend(records)
        time.sleep(0.2)

    print(f"\n[SUCCESS] Retrieved income data for {len(all_records)} Alaska ZCTAs")
    return all_records


CSV_COLUMNS = [
    "zcta",
    "median_income",
    "population",
    "centroid_lat",
    "centroid_lon",
    "acs_year",
    "centroid_method",
    "data_source",
]


def export_records_csv(records: List[Dict], csv_path: str = DEFAULT_CSV_PATH) -> None:
    """Write curated/ingested Alaska ZCTA records to a deterministic UTF-8 CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    ordered = sorted(records, key=lambda r: str(r["zcta"]))
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for rec in ordered:
            writer.writerow({col: rec.get(col, "") for col in CSV_COLUMNS})


def load_records_from_csv(csv_path: str = DEFAULT_CSV_PATH) -> List[Dict]:
    """Load Alaska ZCTA records from an exported CSV snapshot."""
    records: List[Dict] = []
    with open(csv_path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            income = parse_acs_positive_float(row.get("median_income"))
            lat = row.get("centroid_lat")
            lon = row.get("centroid_lon")
            if income is None or not lat or not lon:
                continue
            records.append({
                "zcta": row["zcta"].strip(),
                "median_income": income,
                "population": parse_acs_nonnegative_int(row.get("population")),
                "centroid_lat": float(lat),
                "centroid_lon": float(lon),
                "acs_year": int(row["acs_year"]),
                "centroid_method": (row.get("centroid_method") or "").strip(),
                "data_source": (row.get("data_source") or "").strip(),
            })
    return records


def save_to_database(
    records: List[Dict],
    year: int = DEFAULT_ACS_YEAR,
    clear_existing: bool = False,
) -> Tuple[int, int]:
    """Save Census income records into the CensusIncome SQL table."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if clear_existing:
            deleted = db.query(CensusIncome).delete()
            print(f"Cleared {deleted} existing Census income records")

        saved = 0
        updated = 0
        for record in records:
            zcta = str(record["zcta"]).strip()
            lat = record.get("centroid_lat")
            lon = record.get("centroid_lon")
            if lat is None or lon is None:
                lat, lon = ZCTA_CENTROIDS.get(zcta, (None, None))

            rec_year = int(record.get("acs_year") or year)
            data_source = record.get("data_source") or f"US Census ACS {rec_year} 5-Year"
            population = record.get("population")

            existing = db.query(CensusIncome).filter_by(zcta=zcta).first()
            if existing:
                existing.median_income = float(record["median_income"])
                existing.population = population
                existing.acs_year = rec_year
                existing.centroid_lat = lat
                existing.centroid_lon = lon
                existing.data_source = data_source
                updated += 1
            else:
                db.add(CensusIncome(
                    zcta=zcta,
                    state_fips="02",
                    median_income=float(record["median_income"]),
                    population=population,
                    centroid_lat=lat,
                    centroid_lon=lon,
                    acs_year=rec_year,
                    data_source=data_source,
                ))
                saved += 1

        db.commit()
        print(f"\nSaved {saved} new, updated {updated} existing Census income records")
        return saved, updated
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Census ACS income data for Alaska ZCTAs"
    )
    parser.add_argument(
        "--year", type=int, default=DEFAULT_ACS_YEAR,
        help=f"ACS 5-Year release year (default: {DEFAULT_ACS_YEAR})",
    )
    parser.add_argument(
        "--source", choices=("auto", "bulk", "api"), default="auto",
        help="Data source mode: 'bulk' (no key), 'api' (requires key), or 'auto' (default)",
    )
    parser.add_argument(
        "--key", required=False,
        help="Census API Key (overrides CENSUS_API_KEY env var)",
    )
    parser.add_argument(
        "--cache-dir", required=False, default=None,
        help="Optional local cache directory for downloaded Census files",
    )
    parser.add_argument(
        "--export-csv", default=DEFAULT_CSV_PATH,
        help=f"Output CSV snapshot path (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--skip-csv", action="store_true",
        help="Do not write processed_data CSV snapshot",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="Replace all existing CensusIncome rows instead of upserting",
    )
    args = parser.parse_args()

    api_key = args.key or os.environ.get("CENSUS_API_KEY")
    use_api = args.source == "api" or (args.source == "auto" and bool(api_key))

    print("=" * 60)
    print(f"CENSUS ACS {args.year} 5-YEAR INCOME DATA INGESTION")
    print("=" * 60)

    if use_api:
        if not api_key:
            print("[ERROR] Census API key required for --source api.")
            sys.exit(1)
        records = fetch_all_alaska_income(
            api_key, year=args.year, cache_dir=args.cache_dir
        )
    else:
        records = fetch_bulk_alaska_income(
            year=args.year, cache_dir=args.cache_dir
        )

    if not records:
        print("[ERROR] No Census income records retrieved.")
        sys.exit(1)

    if not args.skip_csv:
        export_records_csv(records, args.export_csv)
        print(f"Exported {len(records)} rows to {args.export_csv}")

    save_to_database(records, year=args.year, clear_existing=args.replace)
    print("\n[SUCCESS] Done!")


if __name__ == "__main__":
    main()

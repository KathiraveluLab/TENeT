import csv
from collections import defaultdict
from pathlib import Path
import h3
import json
import pickle

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

BROADBAND_SOURCES = [
    ("bdc_02_FibertothePremises_fixed_broadband_latest.csv", "fiber"),
    ("bdc_02_Cable_fixed_broadband_latest.csv", "cable"),
    ("bdc_02_LicensedFixedWireless_fixed_broadband_latest.csv", "licensed_fixed_wireless"),
    ("bdc_02_Copper_fixed_broadband_latest.csv", "copper"),
]

TECH_QUALITY_WEIGHT = {
    "fiber": 1.0,
    "cable": 0.85,
    "licensed_fixed_wireless": 0.65,
    "copper": 0.45,
}

H3_RESOLUTION = 8
DOWNLOAD_CAP_MBPS = 100.0
UPLOAD_CAP_MBPS = 20.0

DOWNLOAD_WEIGHT = 0.7
UPLOAD_WEIGHT = 0.3

MAX_USABLE_RTT_MS = 200
MAX_USABLE_PACKET_LOSS_PCT = 10
LATENCY_SCORE_WEIGHT = 0.7
PACKET_LOSS_SCORE_WEIGHT = 0.3

def speed_score(download, upload):
    d = min(download / DOWNLOAD_CAP_MBPS, 1.0)   # cap at 100 Mbps
    u = min(upload / UPLOAD_CAP_MBPS, 1.0)      # cap at 20 Mbps
    return round((DOWNLOAD_WEIGHT * d + UPLOAD_WEIGHT * u), 3)

def load_broadband_by_h3(csv_files):
    h3_map = defaultdict(lambda: defaultdict(float))

    for path, tech in csv_files:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["state_usps"] != "AK":
                    continue

                dl = int(row["max_advertised_download_speed"])
                ul = int(row["max_advertised_upload_speed"])
                latency = int(row["low_latency"])

                if latency == 0:
                    continue

                raw_score = speed_score(dl, ul)
                weighted = raw_score * TECH_QUALITY_WEIGHT[tech]

                h3 = row["h3_res8_id"]
                h3_map[h3][tech] = max(h3_map[h3][tech], weighted)

    return h3_map

def ripe_quality_score(rtt_ms, packet_loss):
    latency_score = max(0.0, 1 - (rtt_ms / MAX_USABLE_RTT_MS))   # 200 ms = unusable
    loss_score = max(0.0, 1 - (packet_loss / MAX_USABLE_PACKET_LOSS_PCT)) # 10% = unusable
    return round(LATENCY_SCORE_WEIGHT * latency_score + PACKET_LOSS_SCORE_WEIGHT * loss_score, 3)

ripe_file = DATA_DIR / "ripe_atlas_ping.json"
def load_ripe_by_h3():
    with open(ripe_file) as f:
        probes = json.load(f)

    h3_scores = defaultdict(list)

    for p in probes:
        loc = p.get("location")
        if not loc:
            continue

        lat = loc["lat"]
        lon = loc["lon"]

        h3_id = h3.latlng_to_cell(lat, lon, H3_RESOLUTION)

        rtt = p["rtt_ms"]["avg"]
        loss = p["packet_loss_pct"]

        score = ripe_quality_score(rtt, loss)
        h3_scores[h3_id].append(score)

    return {
        h3: round(sum(scores) / len(scores), 3)
        for h3, scores in h3_scores.items()
    }


def load_ookla_actual_by_h3():
    with open(DATA_DIR / "alaska_h3_ookla_actual.pkl", "rb") as f:
        return pickle.load(f)

def load_actual_broadband_by_h3():
    ookla_map = load_ookla_actual_by_h3()
    ripe_map = load_ripe_by_h3()
    actual_map = {}

    for h3_id, ookla_score in ookla_map.items():
        ripe_score = ripe_map.get(h3_id)

        if ripe_score is not None:
            actual = round(ookla_score * ripe_score, 3)
        else:
            actual = ookla_score  # no latency data → don't penalize

        actual_map[h3_id] = actual

    return actual_map

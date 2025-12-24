import csv
from collections import defaultdict

TECH_QUALITY_WEIGHT = {
    "fiber": 1.0,
    "cable": 0.85,
    "licensed_fixed_wireless": 0.65,
    "copper": 0.45,
}

def speed_score(download, upload):
    d = min(download / 100, 1.0)   # cap at 100 Mbps
    u = min(upload / 20, 1.0)      # cap at 20 Mbps
    return round((0.7 * d + 0.3 * u), 3)

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


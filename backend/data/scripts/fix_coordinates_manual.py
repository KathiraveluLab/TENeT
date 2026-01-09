#!/usr/bin/env python3
"""
Manual coordinate fixes for Alaska communities using verified sources.
These coordinates are from Wikipedia/official sources for key Alaska places.

Usage:
    python fix_coordinates_manual.py
"""

import os
import csv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'processed_data')
INPUT_FILE = os.path.join(DATA_DIR, 'clean_transport_profiles_1.csv')
OUTPUT_FILE = os.path.join(DATA_DIR, 'clean_transport_profiles_fixed.csv')

# Manually verified coordinates from Wikipedia and official sources
# Format: community_name: (latitude, longitude)
VERIFIED_COORDINATES = {
    # Major cities
    "anchorage": (61.2181, -149.9003),
    "fairbanks": (64.8378, -147.7164),
    "juneau": (58.3019, -134.4197),
    "sitka": (57.0531, -135.3300),
    "ketchikan": (55.3422, -131.6461),
    "wasilla": (61.5814, -149.4394),
    "kodiak": (57.7900, -152.4072),
    "bethel": (60.7922, -161.7558),
    "nome": (64.5011, -165.4064),
    "barrow": (71.2906, -156.7886),  # Utqiagvik
    "utqiagvik": (71.2906, -156.7886),
    "kotzebue": (66.8983, -162.5967),
    "valdez": (61.1308, -146.3483),
    "cordova": (60.5425, -145.7575),
    "homer": (59.6425, -151.5483),
    "kenai": (60.5544, -151.2583),
    "soldotna": (60.4878, -151.0583),
    "seward": (60.1042, -149.4422),
    "palmer": (61.5994, -149.1125),
    
    # Aleutian Islands (commonly misplaced)
    "adak": (51.8800, -176.6581),
    "atka": (52.1967, -174.2006),
    "unalaska": (53.8739, -166.5342),
    "dutch harbor": (53.8894, -166.5422),
    "akutan": (54.1331, -165.7731),
    "cold bay": (55.2064, -162.7181),
    "king cove": (55.0600, -162.3100),
    "sand point": (55.3369, -160.4972),
    "false pass": (54.8533, -163.4106),
    "nikolski": (52.9400, -168.8700),
    "attu": (52.9233, 172.9117),  # Note: positive longitude (across date line)
    "shemya": (52.7228, 174.1256),
    
    # Western Alaska
    "dillingham": (59.0397, -158.4575),
    "king salmon": (58.6883, -156.6614),
    "naknek": (58.7283, -157.0139),
    "togiak": (59.0614, -160.3767),
    "hooper bay": (61.5311, -166.0967),
    "chevak": (61.5278, -165.5864),
    "emmonak": (62.7778, -164.5231),
    "st. mary's": (62.0533, -163.1653),
    "st marys": (62.0533, -163.1653),
    "mountain village": (62.0853, -163.7294),
    "alakanuk": (62.6856, -164.6156),
    "scammon bay": (61.8456, -165.5828),
    "marshall": (61.8767, -162.0756),
    
    # North Slope
    "prudhoe bay": (70.2553, -148.3372),
    "deadhorse": (70.2006, -148.4597),
    "kaktovik": (70.1319, -143.6233),
    "nuiqsut": (70.2106, -150.9956),
    "anaktuvuk pass": (68.1433, -151.7350),
    "point hope": (68.3478, -166.7992),
    "point lay": (69.7328, -163.0053),
    "wainwright": (70.6369, -160.0386),
    
    # Interior Alaska
    "delta junction": (64.0378, -145.7322),
    "tok": (63.3367, -142.9856),
    "glennallen": (62.1089, -145.5467),
    "nenana": (64.5636, -149.0928),
    "healy": (63.8683, -148.9631),
    "manley hot springs": (64.9967, -150.6392),
    "tanana": (65.1722, -152.0756),
    "galena": (64.7344, -156.9256),
    "ruby": (64.7389, -155.4867),
    "mcgrath": (62.9533, -155.5936),
    "holy cross": (62.2014, -159.7728),
    
    # Southeast Alaska
    "haines": (59.2358, -135.4458),
    "skagway": (59.4583, -135.3139),
    "gustavus": (58.4133, -135.7350),
    "yakutat": (59.5469, -139.7272),
    "wrangell": (56.4708, -132.3767),
    "petersburg": (56.8119, -132.9536),
    "craig": (55.4758, -133.1481),
    "klawock": (55.5536, -133.0958),
    "metlakatla": (55.1311, -131.5753),
    "hoonah": (58.1103, -135.4436),
    "angoon": (57.5033, -134.5839),
    "kake": (56.9744, -133.9450),
    "pelican": (57.9600, -136.2283),
    "tenakee springs": (57.7806, -135.2189),
    
    # Kodiak Island
    "kodiak": (57.7900, -152.4072),
    "akhiok": (56.9456, -154.1700),
    "old harbor": (57.2028, -153.3039),
    "larsen bay": (57.5400, -153.9783),
    "ouzinkie": (57.9236, -152.5017),
    "port lions": (57.8675, -152.8833),
    
    # Prince William Sound
    "whittier": (60.7725, -148.6839),
    "tatitlek": (60.8656, -146.6756),
    "chenega bay": (60.0714, -148.0122),
    
    # Yukon-Kuskokwim
    "aniak": (61.5767, -159.5225),
    "russian mission": (61.7856, -161.3194),
    "pilot station": (61.9361, -162.8722),
    "st. michael": (63.4769, -162.1100),
    "st michael": (63.4769, -162.1100),
    "stebbins": (63.5192, -162.2786),
    "unalakleet": (63.8731, -160.7883),
    "shaktoolik": (64.3344, -161.1439),
    "koyuk": (64.9306, -161.1544),
    "elim": (64.6175, -162.2611),
    "golovin": (64.5406, -163.0283),
    "white mountain": (64.6811, -163.4036),
    "teller": (65.2400, -166.3594),
    "brevig mission": (65.3356, -166.4894),
    "wales": (65.6094, -168.0875),
    "diomede": (65.7583, -168.9528),
    "gambell": (63.7797, -171.7381),
    "savoonga": (63.6867, -170.4722),
    
    # Arctic communities
    "buckland": (65.9806, -161.1194),
    "deering": (66.0739, -162.7222),
    "kivalina": (67.7256, -164.5333),
    "noatak": (67.5675, -163.0028),
    "selawik": (66.6039, -160.0069),
    "shungnak": (66.8881, -157.1364),
    "kobuk": (66.9072, -156.8806),
    "ambler": (67.0861, -157.8514),
    "kiana": (66.9744, -160.4236),
    "noorvik": (66.8358, -161.0444),
}


def main():
    print("=" * 60)
    print("MANUAL COORDINATE FIXER")
    print("=" * 60)
    print(f"Using {len(VERIFIED_COORDINATES)} verified coordinate pairs\n")
    
    # Read input CSV
    with open(INPUT_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    print(f"Read {len(rows)} communities from input file\n")
    
    # Update coordinates
    updated = 0
    not_found = []
    
    for row in rows:
        community = row['community'].lower().strip()
        old_lat = float(row['latitude'])
        old_lon = float(row['longitude'])
        
        # Check for match in verified coordinates
        if community in VERIFIED_COORDINATES:
            new_lat, new_lon = VERIFIED_COORDINATES[community]
            
            # Check if significantly different
            if abs(old_lat - new_lat) > 0.01 or abs(old_lon - new_lon) > 0.01:
                print(f"✓ {community}: ({old_lat:.4f}, {old_lon:.4f}) → ({new_lat:.4f}, {new_lon:.4f})")
                row['latitude'] = round(new_lat, 6)
                row['longitude'] = round(new_lon, 6)
                updated += 1
        else:
            not_found.append(community)
    
    # Write output
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total communities: {len(rows)}")
    print(f"  Verified matches: {len(VERIFIED_COORDINATES)}")
    print(f"  Coordinates updated: {updated}")
    print(f"  Not in verified list: {len(not_found)}")
    
    print(f"\n✅ Output saved to: {OUTPUT_FILE}")
    print("\nTo apply changes, run:")
    print(f"  mv '{OUTPUT_FILE}' '{INPUT_FILE}'")
    print("\nThen restart the backend server to reload the data.")


if __name__ == "__main__":
    main()

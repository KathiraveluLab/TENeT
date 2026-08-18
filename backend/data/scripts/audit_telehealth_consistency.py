"""Audit canonical telehealth status consistency on the configured database.

Run against a freshly seeded temporary database, for example:

    DB_PATH=/tmp/tenet-audit.db python data/scripts/audit_telehealth_consistency.py
"""

from __future__ import annotations

import json
import os
import sys


BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_ROOT)

from database.config import SessionLocal  # noqa: E402
from database.models import CATRegion  # noqa: E402
from routes.cat_routes import _build_region_summary  # noqa: E402
from services.research_profile_service import ResearchProfileService  # noqa: E402
from services.scenario_engine import ScenarioEngine  # noqa: E402
from services.scenario_input_cache import ScenarioInputCache  # noqa: E402
from services.telehealth_classification import (  # noqa: E402
    TelehealthClassificationService,
)


def audit_consistency(db):
    ScenarioInputCache.clear()
    regions = db.query(CATRegion).order_by(CATRegion.region_code).all()
    codes = [region.region_code for region in regions]

    summary_lookup = {
        item["region_code"]: item["telehealth_status"]
        for item in _build_region_summary(db, regions)
    }
    profiles, missing_codes = ResearchProfileService.get_profiles(db, codes)
    profile_lookup = {
        profile["region"]["region_code"]: profile["telehealth"]["status"]
        for profile in profiles
    }
    map_lookup = {
        code: context.classification.status
        for code, context in TelehealthClassificationService.classify_regions(
            db, regions
        ).items()
    }
    scenario = ScenarioEngine.preview(db, thresholds={}, region_codes=codes)
    baseline_lookup = {
        item["region_code"]: item["baseline_status"]
        for item in scenario["regions"]
    }
    scenario_lookup = {
        item["region_code"]: item["scenario_status"]
        for item in scenario["regions"]
    }

    mismatches = []
    for code in codes:
        statuses = {
            "summary": summary_lookup.get(code),
            "profile": profile_lookup.get(code),
            "telehealth_map": map_lookup.get(code),
            "scenario_baseline": baseline_lookup.get(code),
            "scenario_default": scenario_lookup.get(code),
        }
        if len(set(statuses.values())) != 1:
            mismatches.append({"region_code": code, "statuses": statuses})

    return {
        "total_communities": len(codes),
        "missing_profiles": missing_codes,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def main():
    db = SessionLocal()
    try:
        result = audit_consistency(db)
    finally:
        db.close()
        ScenarioInputCache.clear()

    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(1 if result["mismatch_count"] else 0)


if __name__ == "__main__":
    main()

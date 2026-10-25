"""Download completed Phase 2/3 trials from ClinicalTrials.gov into a flat CSV.

Usage: python -m backtest.fetch [--max 8000] [--out backtest/data/trials.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request

API = "https://clinicaltrials.gov/api/v2/studies"
QUERY = {
    "filter.overallStatus": "COMPLETED",
    "filter.advanced": (
        "AREA[StudyType]INTERVENTIONAL AND AREA[Phase](PHASE2 OR PHASE3) "
        "AND AREA[StartDate]RANGE[2008-01-01,2022-12-31] AND AREA[EnrollmentCount]RANGE[50,MAX]"
    ),
    "fields": "NCTId|Phase|EnrollmentCount|EnrollmentType|StartDate|PrimaryCompletionDate"
    "|LocationFacility|LeadSponsorClass",
    "pageSize": "500",
}
COLUMNS = ["nct_id", "phase", "enrollment", "enrollment_type", "start", "primary_completion",
           "n_sites", "sponsor_class"]


def get(params: dict) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return json.load(resp)
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))


def flatten(study: dict) -> dict:
    p = study["protocolSection"]
    design = p.get("designModule", {})
    status = p.get("statusModule", {})
    return {
        "nct_id": p["identificationModule"]["nctId"],
        "phase": "/".join(design.get("phases", [])),
        "enrollment": design.get("enrollmentInfo", {}).get("count", ""),
        "enrollment_type": design.get("enrollmentInfo", {}).get("type", ""),
        "start": status.get("startDateStruct", {}).get("date", ""),
        "primary_completion": status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "n_sites": len(p.get("contactsLocationsModule", {}).get("locations", [])),
        "sponsor_class": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class", ""),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=8000)
    ap.add_argument("--out", default="backtest/data/trials.csv")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    rows, token = [], None
    while len(rows) < args.max:
        params = dict(QUERY, **({"pageToken": token} if token else {}))
        page = get(params)
        rows += [flatten(s) for s in page["studies"]]
        token = page.get("nextPageToken")
        print(f"{len(rows)} trials", flush=True)
        if not token:
            break
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows[: args.max])


if __name__ == "__main__":
    main()

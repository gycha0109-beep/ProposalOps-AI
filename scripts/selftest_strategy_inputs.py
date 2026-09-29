#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    fixture = load("evals/strategist/inputs-v1.json")
    by_id = {item["rfp_id"]: item for item in fixture["inputs"]}
    gold_paths = [
        "evals/frozen/v1/dev/strategist/RFP-TEST-001.json",
        "evals/frozen/v1/dev/strategist/RFP-TEST-002.json",
        "evals/frozen/v1/holdout/strategist/RFP-TEST-003.json",
    ]

    missing_assets = []
    leaked_claims = []
    for path in gold_paths:
        gold = load(path)
        rfp_id = gold["input_rfp"]
        item = by_id[rfp_id]
        serialized = json.dumps(item, ensure_ascii=False).lower()
        pack_assets = {ev["asset_id"] for group in item["evidence_packs"] for ev in group.get("evidence", [])}
        for expectation in gold["evidence_expectations"]:
            for asset_id in expectation["allowed_asset_ids"]:
                if asset_id not in pack_assets:
                    missing_assets.append(f"{rfp_id}:{asset_id}")
        for claim in gold.get("forbidden_claims", []):
            if claim.lower() in serialized:
                leaked_claims.append(f"{rfp_id}:{claim}")

    if missing_assets:
        raise SystemExit(f"Missing Strategist evidence assets: {missing_assets}")
    if leaked_claims:
        raise SystemExit(f"Forbidden-claim leakage in Strategist inputs: {leaked_claims}")

    print(json.dumps({"input_count":len(by_id),"missing_assets":0,"forbidden_claim_leaks":0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

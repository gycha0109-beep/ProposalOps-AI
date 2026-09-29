#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evidence_map(pack):
    mapping = {}
    if not pack:
        return mapping
    for group in pack.get("evidence_packs", []):
        for ev in group.get("evidence", []):
            if ev.get("evidence_id") and ev.get("asset_id"):
                mapping[ev["evidence_id"]] = ev["asset_id"]
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--gold", required=True)
    ap.add_argument("--evidence-pack")
    args = ap.parse_args()

    output = load(args.output)
    gold = load(args.gold)
    emap = evidence_map(load(args.evidence_pack)) if args.evidence_pack else {}
    serialized = json.dumps(output, ensure_ascii=False).lower()

    required = gold["required_requirement_ids"]
    covered = [rid for rid in required if rid.lower() in serialized]

    valid_evidence = 0
    evidence_expected = len(gold["evidence_expectations"])
    evidence_details = []

    pillars = output.get("strategy_pillars", [])
    for expectation in gold["evidence_expectations"]:
        rid = expectation["requirement_id"]
        allowed = set(expectation["allowed_asset_ids"])
        cited_ids = []
        for pillar in pillars:
            if rid in pillar.get("rfp_requirement_ids", []):
                cited_ids.extend(pillar.get("evidence_ids", []))
                cited_ids.extend(pillar.get("evidence_asset_ids", []))

        resolved = {emap.get(x, x) for x in cited_ids}
        ok = bool(resolved & allowed)
        valid_evidence += int(ok)
        evidence_details.append({
            "requirement_id": rid,
            "pass": ok,
            "resolved_assets": sorted(resolved),
            "allowed_assets": sorted(allowed),
        })

    forbidden_hits = [
        claim for claim in gold.get("forbidden_claims", [])
        if claim.lower() in serialized
    ]
    info_classes_ok = all(
        item.lower() in serialized
        for item in gold.get("required_information_classes", [])
    )

    result = {
        "track": "proposal_strategist",
        "split": gold.get("split"),
        "metrics": {
            "requirement_coverage": round(len(covered) / len(required), 4) if required else 0,
            "evidence_validity": round(valid_evidence / evidence_expected, 4) if evidence_expected else 0,
            "unsupported_company_claim_count": len(forbidden_hits),
            "information_class_separation": info_classes_ok,
        },
        "covered_requirement_ids": covered,
        "missing_requirement_ids": [x for x in required if x not in covered],
        "forbidden_claim_hits": forbidden_hits,
        "evidence_details": evidence_details,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

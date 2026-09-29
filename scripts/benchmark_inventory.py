#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EXPECTED_V1 = {
    "proposal_count": 12,
    "proposal_asset_count": 51,
    "rfp_count": 3,
    "retrieval_query_count": 36,
    "retrieval_dev_count": 24,
    "retrieval_holdout_count": 12,
    "qa_case_count": 20,
}


def jsonl_count(root):
    total = 0
    ids = set()
    for file in sorted(Path(root).rglob("*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                total += 1
                ids.add(row.get("proposal_id"))
    return total, ids


def build_inventory():
    assets, proposal_ids = jsonl_count("data/processed/proposals")
    rfps = sorted(Path("data/raw/rfps").glob("RFP-TEST-*.md"))
    qa = json.loads(Path("evals/qa-injected-errors/cases.json").read_text(encoding="utf-8"))["cases"]
    dev_ret = json.loads(Path("evals/frozen/v1/dev/retrieval.json").read_text(encoding="utf-8"))["cases"]
    hold_ret = json.loads(Path("evals/frozen/v1/holdout/retrieval.json").read_text(encoding="utf-8"))["cases"]

    return {
        "proposal_count": len(proposal_ids),
        "proposal_asset_count": assets,
        "rfp_count": len(rfps),
        "retrieval_query_count": len(dev_ret) + len(hold_ret),
        "retrieval_dev_count": len(dev_ret),
        "retrieval_holdout_count": len(hold_ret),
        "qa_case_count": len(qa),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assert-v1", action="store_true")
    args = ap.parse_args()

    inventory = build_inventory()
    print(json.dumps(inventory, ensure_ascii=False, indent=2))

    if args.assert_v1:
        mismatches = {
            key: {"expected": expected, "actual": inventory.get(key)}
            for key, expected in EXPECTED_V1.items()
            if inventory.get(key) != expected
        }
        if mismatches:
            print(json.dumps({"benchmark_mismatch": mismatches}, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(1)


if __name__ == "__main__":
    main()

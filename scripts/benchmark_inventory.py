#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


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


assets, proposal_ids = jsonl_count("data/processed/proposals")
rfps = sorted(Path("data/raw/rfps").glob("RFP-TEST-*.md"))
qa = json.loads(Path("evals/qa-injected-errors/cases.json").read_text(encoding="utf-8"))["cases"]
dev_ret = json.loads(Path("evals/frozen/v1/dev/retrieval.json").read_text(encoding="utf-8"))["cases"]
hold_ret = json.loads(Path("evals/frozen/v1/holdout/retrieval.json").read_text(encoding="utf-8"))["cases"]

print(json.dumps({
    "proposal_count": len(proposal_ids),
    "proposal_asset_count": assets,
    "rfp_count": len(rfps),
    "retrieval_query_count": len(dev_ret) + len(hold_ret),
    "retrieval_dev_count": len(dev_ret),
    "retrieval_holdout_count": len(hold_ret),
    "qa_case_count": len(qa),
}, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", help="JSON with results: [{case_id, detected, predicted_type?}]")
    ap.add_argument("--cases", default="evals/qa-injected-errors/cases.json")
    ap.add_argument("--split", required=True)
    args = ap.parse_args()

    all_cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    allowed_ids = set(split["case_ids"])
    cases = {c["id"]: c for c in all_cases if c["id"] in allowed_ids}

    payload = json.loads(Path(args.results).read_text(encoding="utf-8"))
    rows = payload.get("results", payload if isinstance(payload, list) else [])
    by_id = {row["case_id"]: row for row in rows}

    critical = [c for c in cases.values() if c["severity"] == "BLOCK"]
    clean = [c for c in cases.values() if c["type"] == "CLEAN"]

    critical_detected = sum(bool(by_id.get(c["id"], {}).get("detected")) for c in critical)
    false_positive = sum(bool(by_id.get(c["id"], {}).get("detected")) for c in clean)

    type_correct = 0
    typed = 0
    for c in critical:
        row = by_id.get(c["id"], {})
        if row.get("detected") and row.get("predicted_type"):
            typed += 1
            type_correct += int(row["predicted_type"] == c["type"])

    result = {
        "track": "proposal_qa",
        "split": split.get("split"),
        "metrics": {
            "critical_error_detection_recall": round(critical_detected / len(critical), 4) if critical else 0,
            "false_positive_rate": round(false_positive / len(clean), 4) if clean else 0,
            "error_type_accuracy": round(type_correct / typed, 4) if typed else None,
        },
        "critical_total": len(critical),
        "critical_detected": critical_detected,
        "clean_total": len(clean),
        "false_positive_count": false_positive,
        "missing_result_case_ids": sorted(set(cases) - set(by_id)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

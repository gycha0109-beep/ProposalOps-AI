#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--cases", default="evals/qa-injected-errors/cases.json")
    args = ap.parse_args()

    output = json.loads(Path(args.output).read_text(encoding="utf-8"))
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]

    detected = set()
    for item in output.get("blocking_errors", []) + output.get("warnings", []):
        case_id = item.get("case_id")
        if case_id:
            detected.add(case_id)

    critical = {c["id"] for c in cases if c["severity"] == "BLOCK"}
    clean = {c["id"] for c in cases if c["type"] == "CLEAN"}

    tp = len(critical & detected)
    fp = len(clean & detected)

    result = {
        "track": "proposal_qa",
        "critical_total": len(critical),
        "critical_detected": tp,
        "critical_error_detection_recall": round(tp / len(critical), 4) if critical else 0,
        "clean_total": len(clean),
        "false_positive_count": fp,
        "false_positive_rate": round(fp / len(clean), 4) if clean else 0,
        "missed_critical_case_ids": sorted(critical - detected),
        "false_positive_case_ids": sorted(clean & detected)
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def blob(value):
    return json.dumps(value, ensure_ascii=False).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--gold", default="evals/frozen/dev/strategy.json")
    args = ap.parse_args()

    output = json.loads(Path(args.output).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    serialized = blob(output)

    passed = 0
    details = []

    for case in gold["assertions"]:
        metric = case["metric"]
        ok = False

        if metric == "requirement_coverage":
            ok = all(x.lower() in serialized for x in case["required_requirement_ids"])
        elif metric == "evidence_reference":
            ok = any(x.lower() in serialized for x in case["allowed_asset_ids"])
        elif metric == "reference_gap":
            gaps = blob(output.get("reference_gaps", []))
            ok = any(term.lower() in gaps for term in case["expected_terms"])
        elif metric == "forbidden_company_claim":
            ok = not any(x.lower() in serialized for x in case["forbidden_patterns"])
        elif metric == "information_class_separation":
            ok = all(x.lower() in serialized for x in case["expected_classes"])

        passed += int(ok)
        details.append({"id": case["id"], "pass": ok, "critical": case.get("critical", False)})

    total = len(gold["assertions"])
    print(json.dumps({
        "track": "proposal_strategist",
        "passed": passed,
        "total": total,
        "score": round(passed / total, 4) if total else 0,
        "details": details
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

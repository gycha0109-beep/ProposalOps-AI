#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from lib.qa_eval import evaluate_qa_results


def main():
    cases = json.loads(Path("evals/qa-injected-errors/cases.json").read_text(encoding="utf-8"))
    inputs = json.loads(Path("evals/qa-injected-errors/inputs-v1.json").read_text(encoding="utf-8"))
    split = json.loads(Path("evals/frozen/v1/dev/qa.json").read_text(encoding="utf-8"))

    forbidden = {"type", "severity", "reason"}
    leaks = []
    for item in inputs["inputs"]:
        for key in forbidden:
            if key in item:
                leaks.append(f'{item["case_id"]}:{key}')
        draft = item.get("draft", {})
        for key in forbidden:
            if key in draft:
                leaks.append(f'{item["case_id"]}:draft.{key}')
    if leaks:
        raise SystemExit(f"Gold-label leakage found in QA inputs: {leaks}")

    allowed = set(split["case_ids"])
    gold = {c["id"]: c for c in cases["cases"] if c["id"] in allowed}

    perfect = {"results": []}
    missed = {"results": []}
    for case_id in split["case_ids"]:
        c = gold[case_id]
        is_error = c["type"] != "CLEAN"
        perfect["results"].append({
            "case_id": case_id,
            "detected": is_error,
            "predicted_type": c["type"],
            "severity": c["severity"],
            "reason": "self-test",
        })
        missed["results"].append({
            "case_id": case_id,
            "detected": False,
            "predicted_type": "CLEAN",
            "severity": "NONE",
            "reason": "self-test",
        })

    p = evaluate_qa_results(perfect, cases, split)
    m = evaluate_qa_results(missed, cases, split)

    assert p["metrics"]["result_coverage"] == 1.0
    assert p["metrics"]["critical_error_detection_recall"] == 1.0
    assert p["metrics"]["false_positive_rate"] == 0.0
    assert p["metrics"]["error_type_accuracy"] == 1.0
    assert p["metrics"]["severity_accuracy"] == 1.0
    assert m["metrics"]["critical_error_detection_recall"] == 0.0
    assert m["metrics"]["false_positive_rate"] == 0.0

    print(json.dumps({"qa_input_leaks": 0, "perfect_metrics": p["metrics"], "missed_metrics": m["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

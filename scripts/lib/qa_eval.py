from __future__ import annotations

import json
import re
from typing import Any


def parse_qa_output(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^\`\`\`(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\`\`\`$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def evaluate_qa_results(results_payload: dict | list, all_cases: dict, split: dict) -> dict:
    allowed_ids = set(split["case_ids"])
    cases = {c["id"]: c for c in all_cases["cases"] if c["id"] in allowed_ids}

    rows = results_payload.get("results", results_payload if isinstance(results_payload, list) else [])
    if not isinstance(rows, list):
        rows = []
    by_id = {row.get("case_id"): row for row in rows if isinstance(row, dict) and row.get("case_id")}

    block_cases = [c for c in cases.values() if c["severity"] == "BLOCK"]
    warn_cases = [c for c in cases.values() if c["severity"] == "WARN"]
    clean_cases = [c for c in cases.values() if c["type"] == "CLEAN"]
    error_cases = [c for c in cases.values() if c["type"] != "CLEAN"]

    def detected(case):
        return bool(by_id.get(case["id"], {}).get("detected"))

    block_detected = sum(detected(c) for c in block_cases)
    warn_detected = sum(detected(c) for c in warn_cases)
    error_detected = sum(detected(c) for c in error_cases)
    false_positive = sum(detected(c) for c in clean_cases)

    type_correct = 0
    severity_correct = 0
    typed_detected = 0
    severity_typed = 0
    details = []

    for case_id, case in sorted(cases.items()):
        row = by_id.get(case_id, {})
        row_detected = bool(row.get("detected"))
        predicted_type = row.get("predicted_type")
        predicted_severity = row.get("severity")

        expected_detected = case["type"] != "CLEAN"
        type_ok = None
        severity_ok = None

        if expected_detected and row_detected and predicted_type:
            typed_detected += 1
            type_ok = predicted_type == case["type"]
            type_correct += int(type_ok)

        if expected_detected and row_detected and predicted_severity:
            severity_typed += 1
            severity_ok = predicted_severity == case["severity"]
            severity_correct += int(severity_ok)

        details.append({
            "case_id": case_id,
            "expected_type": case["type"],
            "expected_severity": case["severity"],
            "expected_detected": expected_detected,
            "detected": row_detected,
            "predicted_type": predicted_type,
            "predicted_severity": predicted_severity,
            "type_correct": type_ok,
            "severity_correct": severity_ok,
            "reason": row.get("reason"),
        })

    case_count = len(cases)
    result_count = len(set(by_id) & set(cases))

    return {
        "track": "proposal_qa",
        "evaluator_version": "1.1",
        "split": split.get("split"),
        "case_count": case_count,
        "result_count": result_count,
        "metrics": {
            "result_coverage": round(result_count / case_count, 4) if case_count else 0.0,
            "critical_error_detection_recall": round(block_detected / len(block_cases), 4) if block_cases else None,
            "warning_detection_recall": round(warn_detected / len(warn_cases), 4) if warn_cases else None,
            "all_error_detection_recall": round(error_detected / len(error_cases), 4) if error_cases else None,
            "false_positive_rate": round(false_positive / len(clean_cases), 4) if clean_cases else None,
            "error_type_accuracy": round(type_correct / typed_detected, 4) if typed_detected else None,
            "severity_accuracy": round(severity_correct / severity_typed, 4) if severity_typed else None,
        },
        "counts": {
            "block_total": len(block_cases),
            "block_detected": block_detected,
            "warn_total": len(warn_cases),
            "warn_detected": warn_detected,
            "clean_total": len(clean_cases),
            "false_positive_count": false_positive,
        },
        "missing_result_case_ids": sorted(set(cases) - set(by_id)),
        "unexpected_result_case_ids": sorted(set(by_id) - set(cases)),
        "details": details,
    }

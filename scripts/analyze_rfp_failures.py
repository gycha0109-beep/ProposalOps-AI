#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED_TOP_LEVEL = {"project", "scope", "deliverables", "requirements", "evaluation", "constraints"}


def classify(record):
    evaluation = record["evaluation"]
    parsed = record.get("parsed_output")
    failures = []

    if parsed is None:
        failures.append("INVALID_JSON")
    if evaluation.get("output_truncated"):
        failures.append("OUTPUT_TRUNCATION")

    schema_valid = evaluation["metrics"].get("canonical_schema_valid")
    if schema_valid is not None and schema_valid < 1.0:
        failures.append("SCHEMA_DRIFT")
    elif isinstance(parsed, dict):
        missing = REQUIRED_TOP_LEVEL - set(parsed)
        aliases = {"project_overview", "evaluations"} & set(parsed)
        if missing or aliases:
            failures.append("SCHEMA_DRIFT")

    metrics = evaluation["metrics"]
    if metrics.get("source_quote_coverage", 0) < 0.9:
        failures.append("MISSING_SOURCE_QUOTE")
    validity = metrics.get("source_quote_validity")
    if validity is not None and validity < 1.0:
        failures.append("INVALID_SOURCE_QUOTE")
    if metrics.get("unsupported_addition_count", 0) > 0:
        failures.append("UNSUPPORTED_ADDITION")

    for detail in evaluation.get("details", []):
        if detail.get("pass"):
            continue
        metric = detail.get("metric")
        if metric in {"requirement_terms", "requirement_present"}:
            failures.append("MISSING_REQUIREMENT")
        elif metric == "unknown":
            failures.append("UNKNOWN_POLICY_FAILURE")
        elif metric in {"deliverable", "evaluation_sum", "exact_or_semantic"}:
            failures.append("FACT_OR_NUMERIC_MISMATCH")

    return sorted(set(failures))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    rows = []
    counts = Counter()
    for path in sorted(Path(args.root).rglob("run-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        failure_types = classify(record)
        counts.update(failure_types)
        rows.append({
            "run_id": record["run_id"],
            "prompt_version": record["prompt_version"],
            "rfp_id": record["input"]["rfp_id"],
            "failure_types": failure_types,
            "raw_path": str(path),
        })

    result = {
        "run_count": len(rows),
        "failure_type_counts": dict(sorted(counts.items())),
        "runs": rows,
    }

    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# RFP Analyzer Failure Taxonomy", "", f"- raw runs: **{len(rows)}**", "", "## Counts", "", "| Type | Count |", "|---|---:|"]
    for key, value in sorted(counts.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Runs", ""])
    for row in rows:
        labels = ", ".join(row["failure_types"]) if row["failure_types"] else "NONE"
        lines.append(f'- `{row["prompt_version"]}` / `{row["rfp_id"]}` → {labels}')

    md_path = Path(args.md_out)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

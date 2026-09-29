#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


METRICS = (
    "result_coverage",
    "critical_error_detection_recall",
    "warning_detection_recall",
    "all_error_detection_recall",
    "false_positive_rate",
    "error_type_accuracy",
    "severity_accuracy",
)


def numeric(values):
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def summarize(records):
    data = {
        "run_count": len(records),
        "json_parseable_rate": round(sum(bool(r.get("json_parseable")) for r in records) / len(records), 4),
        "metrics": {},
        "usage": {},
    }
    for metric in METRICS:
        values = numeric([r["evaluation"]["metrics"].get(metric) for r in records])
        if not values:
            data["metrics"][metric] = None
        else:
            data["metrics"][metric] = {
                "mean": round(statistics.mean(values), 4),
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "stdev": round(statistics.pstdev(values), 4),
            }

    for key in ("input_tokens", "output_tokens", "total_tokens"):
        values = numeric([(r.get("metadata", {}).get("usage") or {}).get(key) for r in records])
        if values:
            data["usage"][key] = {"total": sum(values), "mean": round(statistics.mean(values), 2)}

    reasoning = numeric([(((r.get("metadata", {}).get("usage") or {}).get("output_tokens_details") or {}).get("reasoning_tokens")) for r in records])
    if reasoning:
        data["usage"]["reasoning_tokens"] = {"total": sum(reasoning), "mean": round(statistics.mean(reasoning), 2)}

    data["failed_cases"] = [
        {
            "run_id": r["run_id"],
            "case_ids": [d["case_id"] for d in r["evaluation"]["details"] if d["expected_detected"] != d["detected"]],
        }
        for r in records
    ]
    return data


def fmt(metric):
    if metric is None:
        return "-"
    return f'{metric["mean"]:.2%}'


def render(result):
    lines = [
        f'# Proposal QA Benchmark — {result["split"]}',
        "",
        f'- benchmark: `{result["benchmark_version"]}`',
        f'- model: `{result["model"]}`',
        f'- reasoning effort: `{result["parameters"].get("reasoning_effort", result["parameters"].get("thinking_level", "-"))}`',
        f'- runs: **{result["run_count"]}**',
        "",
        "| Version | JSON | Coverage | BLOCK recall | WARN recall | All error recall | False positive | Type accuracy | Severity accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version, data in result["versions"].items():
        m = data["metrics"]
        lines.append(
            "| " + " | ".join([
                version,
                f'{data["json_parseable_rate"]:.2%}',
                fmt(m["result_coverage"]),
                fmt(m["critical_error_detection_recall"]),
                fmt(m["warning_detection_recall"]),
                fmt(m["all_error_detection_recall"]),
                fmt(m["false_positive_rate"]),
                fmt(m["error_type_accuracy"]),
                fmt(m["severity_accuracy"]),
            ]) + " |"
        )
    lines.extend([
        "",
        "Synthetic injected-error benchmark. Raw outputs are retained; clean-case false positives are not discarded.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    args = parser.parse_args()

    records = []
    for path in sorted(Path(args.root).rglob("run-*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise SystemExit(f"No QA runs found under {args.root}")

    groups = defaultdict(list)
    for r in records:
        groups[r["prompt_version"]].append(r)

    first = records[0]
    result = {
        "track": "proposal_qa",
        "benchmark_version": first["benchmark_version"],
        "split": first["split"],
        "model": first["model"],
        "parameters": first["parameters"],
        "run_count": len(records),
        "versions": {version: summarize(rows) for version, rows in sorted(groups.items())},
    }

    rendered_json = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        p = Path(args.json_out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(rendered_json, encoding="utf-8")
    else:
        print(rendered_json, end="")
    if args.md_out:
        p = Path(args.md_out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


METRICS = (
    "result_coverage",
    "primary_asset_recall",
    "selected_asset_precision",
    "prohibited_asset_rejection",
    "provenance_validity",
    "status_accuracy",
    "company_fact_violation_count",
    "unsupported_numeric_claim_count",
    "evidence_id_violation_count",
)


def numeric(values):
    return [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]


def summarize(records):
    data = {
        "run_count": len(records),
        "json_parseable_rate": round(sum(bool(r.get("json_parseable")) for r in records) / len(records), 4),
        "pass_rate": round(sum(bool((r.get("evaluation") or {}).get("pass")) for r in records) / len(records), 4),
        "metrics": {},
        "usage": {},
    }
    for metric in METRICS:
        values = numeric([(r.get("evaluation") or {}).get("metrics", {}).get(metric) for r in records])
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
    return data


def pct(metric):
    return "-" if metric is None else f'{metric["mean"]:.2%}'


def count(metric):
    return "-" if metric is None else f'{metric["mean"]:.2f}'


def render(result):
    lines = [
        "# Evidence Builder Benchmark — dev",
        "",
        f'- benchmark: `{result["benchmark_version"]}`',
        f'- model: `{result["model"]}`',
        f'- runs: **{result["run_count"]}**',
        "",
        "| Version | JSON | PASS | Primary recall | Precision | Reject prohibited | Provenance | Status | Company violations | Numeric violations |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version, data in result["versions"].items():
        m = data["metrics"]
        lines.append(
            "| " + " | ".join([
                version,
                f'{data["json_parseable_rate"]:.2%}',
                f'{data["pass_rate"]:.2%}',
                pct(m["primary_asset_recall"]),
                pct(m["selected_asset_precision"]),
                pct(m["prohibited_asset_rejection"]),
                pct(m["provenance_validity"]),
                pct(m["status_accuracy"]),
                count(m["company_fact_violation_count"]),
                count(m["unsupported_numeric_claim_count"]),
            ]) + " |"
        )
    lines.extend([
        "",
        "The six cases use real Dify semantic top-5 retrieval results from RFP-TEST-002.",
        "Hard-negative assets remain in candidate lists where retrieval returned them.",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    args = parser.parse_args()

    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(Path(args.root).rglob("run-*.json"))
    ]
    if not records:
        raise SystemExit(f"No Evidence Builder runs found under {args.root}")

    groups = defaultdict(list)
    for record in records:
        groups[record["prompt_version"]].append(record)

    first = records[0]
    result = {
        "track": "evidence_builder",
        "benchmark_version": first["benchmark_version"],
        "split": first["split"],
        "model": first["model"],
        "parameters": first["parameters"],
        "run_count": len(records),
        "versions": {version: summarize(rows) for version, rows in sorted(groups.items())},
    }

    raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")

    if args.md_out:
        path = Path(args.md_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()

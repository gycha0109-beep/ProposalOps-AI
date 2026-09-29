#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


METRICS = (
    "result_coverage",
    "requirement_coverage",
    "evidence_citation_coverage",
    "evidence_validity",
    "unsupported_company_claim_count",
    "unsupported_quantitative_claim_count",
    "information_class_separation",
    "invalid_evidence_reference_count",
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
    return data


def fmt(metric):
    if metric is None:
        return "-"
    return f'{metric["mean"]:.2%}'


def fmt_count(metric):
    if metric is None:
        return "-"
    return f'{metric["mean"]:.2f}'


def render(result):
    lines = [
        f'# Proposal Strategist Benchmark — {result["split"]}',
        "",
        f'- benchmark: `{result["benchmark_version"]}`',
        f'- model: `{result["model"]}`',
        f'- reasoning effort: `{result["parameters"].get("reasoning_effort", result["parameters"].get("thinking_level", "-"))}`',
        f'- runs: **{result["run_count"]}**',
        "",
        "| Version | JSON | Result coverage | Requirement | Citation | Evidence valid | Info class | Unsupported company | Unsupported quantitative | Invalid evidence |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version, data in result["versions"].items():
        m = data["metrics"]
        lines.append(
            "| " + " | ".join([
                version,
                f'{data["json_parseable_rate"]:.2%}',
                fmt(m["result_coverage"]),
                fmt(m["requirement_coverage"]),
                fmt(m["evidence_citation_coverage"]),
                fmt(m["evidence_validity"]),
                fmt(m["information_class_separation"]),
                fmt_count(m["unsupported_company_claim_count"]),
                fmt_count(m["unsupported_quantitative_claim_count"]),
                fmt_count(m["invalid_evidence_reference_count"]),
            ]) + " |"
        )
    lines.extend(["", "Synthetic frozen benchmark. Raw outputs and failures are retained.", ""])
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
        raise SystemExit(f"No Strategist runs found under {args.root}")

    groups = defaultdict(list)
    for r in records:
        groups[r["prompt_version"]].append(r)

    first = records[0]
    result = {
        "track": "proposal_strategist",
        "benchmark_version": first["benchmark_version"],
        "split": first["split"],
        "model": first["model"],
        "parameters": first["parameters"],
        "run_count": len(records),
        "versions": {version: summarize(rows) for version, rows in sorted(groups.items())},
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        p=Path(args.json_out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.md_out:
        p=Path(args.md_out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(render(result), encoding="utf-8")


if __name__ == "__main__":
    main()

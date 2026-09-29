#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


METRICS = (
    "assertion_pass_rate",
    "deliverable_recall",
    "numeric_fidelity",
    "requirement_assertion_recall",
    "unsupported_addition_count",
    "source_quote_coverage",
    "source_quote_validity",
    "canonical_schema_valid",
)


def load_runs(root: Path) -> list[dict]:
    runs = []
    for path in sorted(root.rglob("run-*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["_path"] = str(path)
        runs.append(record)
    return runs


def numeric(values):
    return [value for value in values if isinstance(value, (int, float))]


def summarize_version(records: list[dict]) -> dict:
    summary = {
        "run_count": len(records),
        "rfp_ids": sorted({r["input"]["rfp_id"] for r in records}),
        "json_parseable_rate": round(
            sum(bool(r["evaluation"]["json_parseable"]) for r in records) / len(records),
            4,
        ),
        "output_truncated_rate": round(
            sum(bool(r["evaluation"].get("output_truncated")) for r in records) / len(records),
            4,
        ),
        "metrics": {},
        "usage": {},
    }

    for metric in METRICS:
        values = numeric([
            r["evaluation"]["metrics"].get(metric)
            for r in records
        ])
        if not values:
            summary["metrics"][metric] = None
            continue

        summary["metrics"][metric] = {
            "mean": round(statistics.mean(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "stdev": round(statistics.pstdev(values), 4),
        }

    for usage_key in ("input_tokens", "output_tokens", "total_tokens"):
        values = numeric([
            (r.get("metadata", {}).get("usage") or {}).get(usage_key)
            for r in records
        ])
        if values:
            summary["usage"][usage_key] = {
                "total": sum(values),
                "mean": round(statistics.mean(values), 2),
            }

    reasoning_values = numeric([
        (
            ((r.get("metadata", {}).get("usage") or {}).get("output_tokens_details") or {})
            .get("reasoning_tokens")
        )
        for r in records
    ])
    if reasoning_values:
        summary["usage"]["reasoning_tokens"] = {
            "total": sum(reasoning_values),
            "mean": round(statistics.mean(reasoning_values), 2),
        }

    failures = []
    for record in records:
        failed = [
            item["id"]
            for item in record["evaluation"]["details"]
            if not item["pass"]
        ]
        if failed:
            failures.append({
                "run_id": record["run_id"],
                "rfp_id": record["input"]["rfp_id"],
                "failed_case_ids": failed,
            })
    summary["failed_assertions"] = failures

    return summary


def render_markdown(result: dict) -> str:
    lines = [
        f'# RFP Analyzer Benchmark — {result["split"]}',
        "",
        f'- benchmark: {result["benchmark_version"]}',
        f'- model: {result["model"]}',
        f'- thinking level: {result["parameters"].get("thinking_level", result["parameters"].get("reasoning_effort", "-"))}',
        f'- runs: **{result["run_count"]}**',
        "",
        "## Version comparison",
        "",
        "| Version | Runs | JSON | Schema | Truncated | Assertion | Deliverable | Numeric | Requirement | Quote coverage | Quote validity | Unsupported |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def fmt_metric(data):
        if data is None:
            return "-"
        return f'{data["mean"]:.2%}'

    for version, data in result["versions"].items():
        unsupported = data["metrics"]["unsupported_addition_count"]
        unsupported_text = "-" if unsupported is None else f'{unsupported["mean"]:.2f}'
        lines.append(
            "| "
            + " | ".join([
                version,
                str(data["run_count"]),
                f'{data["json_parseable_rate"]:.2%}',
                fmt_metric(data["metrics"]["canonical_schema_valid"]),
                f'{data["output_truncated_rate"]:.2%}',
                fmt_metric(data["metrics"]["assertion_pass_rate"]),
                fmt_metric(data["metrics"]["deliverable_recall"]),
                fmt_metric(data["metrics"]["numeric_fidelity"]),
                fmt_metric(data["metrics"]["requirement_assertion_recall"]),
                fmt_metric(data["metrics"]["source_quote_coverage"]),
                fmt_metric(data["metrics"]["source_quote_validity"]),
                unsupported_text,
            ])
            + " |"
        )

    lines.extend([
        "",
        "## Interpretation rule",
        "",
        "이 보고서는 frozen benchmark의 raw run을 기계적으로 집계한다. "
        "synthetic benchmark 결과이며 실제 고객 생산성 개선 수치로 해석하지 않는다.",
        "",
        "실패 run은 삭제하지 않고 runs/에 그대로 보존한다.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="runs/rfp_analyzer/benchmark-v1/dev",
    )
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    args = parser.parse_args()

    root = Path(args.root)
    runs = load_runs(root)
    if not runs:
        raise SystemExit(f"No raw runs found under {root}")

    groups = defaultdict(list)
    for record in runs:
        groups[record["prompt_version"]].append(record)

    first = runs[0]
    result = {
        "track": "rfp_analyzer",
        "benchmark_version": first["benchmark_version"],
        "split": first["split"],
        "model": first["model"],
        "parameters": first["parameters"],
        "run_count": len(runs),
        "versions": {
            version: summarize_version(records)
            for version, records in sorted(groups.items())
        },
    }

    rendered_json = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    rendered_md = render_markdown(result)

    if args.json_out:
        path = Path(args.json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered_json, encoding="utf-8")
    else:
        print(rendered_json, end="")

    if args.md_out:
        path = Path(args.md_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered_md, encoding="utf-8")


if __name__ == "__main__":
    main()

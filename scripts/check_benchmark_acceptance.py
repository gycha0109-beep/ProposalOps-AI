#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--acceptance", required=True)
    parser.add_argument("--version")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    acceptance = json.loads(Path(args.acceptance).read_text(encoding="utf-8"))
    version = args.version or acceptance["candidate"]
    data = report["versions"].get(version)
    if data is None:
        raise SystemExit(f"Version not found: {version}")

    rules = acceptance["criteria"]
    failures = []
    if data["run_count"] < rules["run_count"]["min"]:
        failures.append(f'run_count={data["run_count"]}')
    if "json_parseable_rate" in rules and data["json_parseable_rate"] < rules["json_parseable_rate"]["min"]:
        failures.append(f'json_parseable_rate={data["json_parseable_rate"]}')
    if "output_truncated_rate" in rules and data.get("output_truncated_rate", 0) > rules["output_truncated_rate"]["max"]:
        failures.append(f'output_truncated_rate={data.get("output_truncated_rate", 0)}')

    for metric, rule in rules.items():
        if metric in {"run_count", "json_parseable_rate", "output_truncated_rate"}:
            continue
        value = data["metrics"].get(metric)
        if value is None:
            failures.append(f"{metric}=missing")
            continue
        if "mean_min" in rule and value["mean"] < rule["mean_min"]:
            failures.append(f'{metric}.mean={value["mean"]}')
        if "min_min" in rule and value["min"] < rule["min_min"]:
            failures.append(f'{metric}.min={value["min"]}')
        if "mean_max" in rule and value["mean"] > rule["mean_max"]:
            failures.append(f'{metric}.mean={value["mean"]}')
        if "max_max" in rule and value["max"] > rule["max_max"]:
            failures.append(f'{metric}.max={value["max"]}')

    result = {"version": version, "accepted": not failures, "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

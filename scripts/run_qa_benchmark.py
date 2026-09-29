#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from lib.openai_responses import ProviderError, call_openai_responses, get_openai_api_key
from lib.qa_eval import evaluate_qa_results, parse_qa_output


DEFAULT_CONFIG = "configs/proposal-qa-benchmark-v1.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_commit():
    github_sha = os.environ.get("GITHUB_SHA", "").strip()
    if github_sha:
        return github_sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def extract_prompt_body(content):
    markers = ["## Error Types", "## Blocking Errors", "## Prompt"]
    positions = [(content.find(marker), marker) for marker in markers if marker in content]
    if not positions:
        return content.strip()
    pos, _ = min(positions, key=lambda item: item[0])
    return content[pos:].strip()


def parse_versions(value, available):
    if value == "all":
        return list(available)
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in requested if item not in available]
    if unknown:
        raise SystemExit(f"Unknown prompt versions: {', '.join(unknown)}")
    return requested


def build_batch(config, split_name):
    split = load_json(config["splits"][split_name])
    fixture = load_json(config["inputs_file"])
    by_id = {item["case_id"]: item for item in fixture["inputs"]}
    missing = [case_id for case_id in split["case_ids"] if case_id not in by_id]
    if missing:
        raise SystemExit(f"Missing neutral QA inputs: {missing}")
    return split, [by_id[case_id] for case_id in split["case_ids"]]


def output_contract():
    return '''
## Benchmark Output Contract

Return JSON only. Do not use Markdown fences.

{"results":[{"case_id":"QA-001","detected":true,"predicted_type":"string","severity":"string","reason":"short explanation"}]}

Rules:
- Return exactly one result for every input case_id.
- detected=true only when the provided draft/context contains a QA issue.
- If no issue exists, use detected=false, predicted_type="CLEAN", severity="NONE".
- For detected issues, use the most specific error type and severity supported by your QA rules.
- Evaluate only the supplied context. Do not invent missing company facts or evidence.
'''


def run_one(config, version, split_name, split, batch, api_key, commit):
    prompt_path = Path(config["versions"][version])
    prompt_content = prompt_path.read_text(encoding="utf-8")
    instructions = extract_prompt_body(prompt_content) + "\n\n" + output_contract()
    parameters = config["parameters"]

    input_payload = {
        "task": "Review each proposal QA case independently.",
        "split": split_name,
        "cases": batch,
    }

    response = call_openai_responses(
        api_key=api_key,
        model=config["model"],
        reasoning_effort=parameters["reasoning_effort"],
        max_output_tokens=parameters["max_output_tokens"],
        instructions=instructions,
        input_text=json.dumps(input_payload, ensure_ascii=False, indent=2),
        max_retries=int(parameters.get("max_retries", 2)),
        retry_delay_seconds=int(parameters.get("retry_delay_seconds", 5)),
    )

    raw_output = response["output_text"]
    parsed = parse_qa_output(raw_output)
    all_cases = load_json(config["cases_file"])
    evaluation = evaluate_qa_results(parsed or {}, all_cases, split)

    return {
        "run_id": f'proposal_qa-{config["benchmark_version"]}-{split_name}-{version}-01',
        "track": "proposal_qa",
        "benchmark_version": config["benchmark_version"],
        "split": split_name,
        "prompt_version": version,
        "prompt_file": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt_content.encode("utf-8")).hexdigest(),
        "model": response["model"],
        "parameters": {
            "reasoning_effort": parameters["reasoning_effort"],
            "max_output_tokens": parameters["max_output_tokens"],
            "max_retries": parameters.get("max_retries", 2),
            "retry_delay_seconds": parameters.get("retry_delay_seconds", 5),
        },
        "input": {
            "case_ids": split["case_ids"],
            "inputs_file": config["inputs_file"],
            "cases_file": config["cases_file"],
            "split_file": config["splits"][split_name],
        },
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": commit,
            "provider": response["provider"],
            "provider_response_id": response["response_id"],
            "latency_seconds": response["latency_seconds"],
            "retry_count": response.get("retry_count", 0),
            "usage": response["usage"],
        },
        "raw_output": raw_output,
        "parsed_output": parsed,
        "json_parseable": parsed is not None,
        "evaluation": evaluation,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--split", choices=("dev", "holdout"), default="dev")
    parser.add_argument("--versions", default="all")
    parser.add_argument("--output-root")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--confirm-holdout", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    versions = parse_versions(args.versions, config["versions"])
    split, batch = build_batch(config, args.split)

    if args.split == "holdout" and not args.plan_only and not args.confirm_holdout:
        raise SystemExit("Holdout execution is protected. Freeze a candidate before final holdout use.")

    plan = {
        "track": config["track"],
        "benchmark_version": config["benchmark_version"],
        "provider": config["provider"],
        "model": config["model"],
        "split": args.split,
        "case_count": len(batch),
        "prompt_versions": versions,
        "planned_calls": len(versions),
    }

    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if config["provider"] != "openai":
        raise SystemExit(f'Unsupported provider: {config["provider"]}')

    try:
        api_key = get_openai_api_key()
    except ProviderError as exc:
        raise SystemExit(str(exc)) from exc

    commit = git_commit()
    root = Path(args.output_root or f'runs/proposal_qa/{config["run_namespace"]}')
    completed = 0
    failed = 0

    for version in versions:
        path = root / args.split / version / "run-01.json"
        if path.exists() and not args.overwrite:
            print(f"SKIP existing: {path}")
            continue

        print(f"RUN {args.split} {version} cases={len(batch)}")
        try:
            record = run_one(config, version, args.split, split, batch, api_key, commit)
        except ProviderError as exc:
            failure = root / args.split / "_failures" / f"{version}.json"
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_text(
                json.dumps({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "prompt_version": version,
                    "split": args.split,
                    "error": str(exc),
                    "git_commit": commit,
                }, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            failed += 1
            print(f"  FAILED: {exc}")
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        completed += 1
        m = record["evaluation"]["metrics"]
        print(f'  block_recall={m["critical_error_detection_recall"]} fp={m["false_positive_rate"]} type={m["error_type_accuracy"]}')

    print(f"completed={completed} failed={failed} planned={len(versions)}")
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

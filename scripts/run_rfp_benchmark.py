#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.gemini_generate_content import (
    ProviderError,
    call_gemini_generate_content,
    get_gemini_api_key,
)
from lib.rfp_eval import evaluate_rfp, parse_json_output


DEFAULT_CONFIG = "configs/rfp-analyzer-benchmark-v1.json"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_commit() -> str:
    github_sha = os.environ.get("GITHUB_SHA", "").strip()
    if github_sha:
        return github_sha

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def extract_prompt_body(content: str) -> str:
    for marker in ("## Prompt", "## Role"):
        if marker in content:
            return content.split(marker, 1)[1].strip()
    return content.strip()


def parse_versions(value: str, available: dict[str, str]) -> list[str]:
    if value == "all":
        return list(available)

    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in requested if item not in available]
    if unknown:
        raise SystemExit(f"Unknown prompt versions: {', '.join(unknown)}")
    return requested


def validate_case(case: dict) -> None:
    for field in ("rfp_id", "input", "gold"):
        if not case.get(field):
            raise SystemExit(f"Benchmark case is missing '{field}': {case}")

    for field in ("input", "gold"):
        if not Path(case[field]).exists():
            raise SystemExit(f"Missing benchmark file: {case[field]}")


def build_plan(config: dict, split: str, versions: list[str], repetitions: int) -> list[dict]:
    plan = []
    for case in config["cases"][split]:
        validate_case(case)
        for version in versions:
            prompt_path = config["versions"][version]
            if not Path(prompt_path).exists():
                raise SystemExit(f"Missing prompt file: {prompt_path}")

            for repeat in range(1, repetitions + 1):
                plan.append(
                    {
                        "split": split,
                        "rfp_id": case["rfp_id"],
                        "prompt_version": version,
                        "repeat": repeat,
                        "input": case["input"],
                        "gold": case["gold"],
                        "prompt": prompt_path,
                    }
                )
    return plan


def output_path(base: Path, item: dict) -> Path:
    return (
        base
        / item["split"]
        / item["prompt_version"]
        / item["rfp_id"]
        / f'run-{item["repeat"]:02d}.json'
    )


def run_one(config: dict, item: dict, api_key: str, commit: str) -> dict:
    prompt_file = Path(item["prompt"])
    prompt_content = prompt_file.read_text(encoding="utf-8")
    instructions = extract_prompt_body(prompt_content)

    rfp_text = Path(item["input"]).read_text(encoding="utf-8")
    gold = load_json(item["gold"])

    model = config["model"]
    parameters = config["parameters"]

    response = call_gemini_generate_content(
        api_key=api_key,
        model=model,
        thinking_level=parameters["thinking_level"],
        max_output_tokens=parameters["max_output_tokens"],
        system_instruction=instructions,
        input_text=(
            f'RFP ID: {item["rfp_id"]}\n\n'
            f'{rfp_text}'
        ),
        max_503_retries=int(parameters.get("max_503_retries", 1)),
        retry_delay_seconds=int(parameters.get("retry_delay_seconds", 12)),
    )

    raw_output = response["output_text"]
    evaluation = evaluate_rfp(raw_output, gold)
    parsed = parse_json_output(raw_output)

    return {
        "run_id": (
            f'{config["track"]}-{config["benchmark_version"]}-'
            f'{item["split"]}-{item["prompt_version"]}-'
            f'{item["rfp_id"]}-{item["repeat"]:02d}'
        ),
        "track": config["track"],
        "benchmark_version": config["benchmark_version"],
        "split": item["split"],
        "prompt_version": item["prompt_version"],
        "prompt_file": item["prompt"],
        "prompt_sha256": hashlib.sha256(prompt_content.encode("utf-8")).hexdigest(),
        "model": response["model"],
        "parameters": {
            "thinking_level": parameters["thinking_level"],
            "max_output_tokens": parameters["max_output_tokens"],
            "request_delay_seconds": parameters.get("request_delay_seconds", 0),
            "max_503_retries": parameters.get("max_503_retries", 1),
            "retry_delay_seconds": parameters.get("retry_delay_seconds", 12),
        },
        "input": {
            "rfp_id": item["rfp_id"],
            "source_file": item["input"],
            "gold_file": item["gold"],
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
        "evaluation": evaluation,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--split", choices=("dev", "holdout"), default="dev")
    parser.add_argument("--versions", default="all")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--output-root")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--confirm-holdout", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    versions = parse_versions(args.versions, config["versions"])
    repetitions = args.repetitions or config["repetitions"][args.split]

    if repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")

    if args.split == "holdout" and not args.plan_only and not args.confirm_holdout:
        raise SystemExit(
            "Holdout execution is protected. Re-run with --confirm-holdout only "
            "after the final prompt candidate is frozen."
        )

    plan = build_plan(config, args.split, versions, repetitions)

    if args.plan_only:
        print(
            json.dumps(
                {
                    "benchmark_version": config["benchmark_version"],
                    "track": config["track"],
                    "provider": config["provider"],
                    "model": config["model"],
                    "parameters": config["parameters"],
                    "split": args.split,
                    "prompt_versions": versions,
                    "repetitions": repetitions,
                    "planned_calls": len(plan),
                    "plan": plan,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if config["provider"] != "gemini":
        raise SystemExit(f'Unsupported provider: {config["provider"]}')

    try:
        api_key = get_gemini_api_key()
    except ProviderError as exc:
        raise SystemExit(str(exc)) from exc

    commit = git_commit()
    run_namespace = config.get("run_namespace", f'benchmark-{config["benchmark_version"]}')
    root = Path(args.output_root or f"runs/rfp_analyzer/{run_namespace}")
    delay = float(config["parameters"].get("request_delay_seconds", 0))

    completed = 0
    for index, item in enumerate(plan):
        path = output_path(root, item)
        if path.exists() and not args.overwrite:
            print(f"SKIP existing: {path}")
            continue

        if completed > 0 and delay > 0:
            time.sleep(delay)

        print(
            f'RUN {index + 1}/{len(plan)} '
            f'{item["split"]} {item["prompt_version"]} '
            f'{item["rfp_id"]} repeat={item["repeat"]}'
        )

        try:
            record = run_one(config, item, api_key, commit)
        except ProviderError as exc:
            failure_path = root / item["split"] / "_failures" / (
                f'{item["prompt_version"]}-{item["rfp_id"]}-'
                f'{item["repeat"]:02d}.json'
            )
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            failure_path.write_text(
                json.dumps(
                    {
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "prompt_version": item["prompt_version"],
                        "rfp_id": item["rfp_id"],
                        "repeat": item["repeat"],
                        "error": str(exc),
                        "git_commit": commit,
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            raise SystemExit(f"Model call failed: {exc}") from exc

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        completed += 1

        metrics = record["evaluation"]["metrics"]
        print(
            f'  assertion={metrics["assertion_pass_rate"]:.4f} '
            f'numeric={metrics["numeric_fidelity"]} '
            f'unsupported={metrics["unsupported_addition_count"]}'
        )

    print(f"completed={completed} planned={len(plan)}")


if __name__ == "__main__":
    main()

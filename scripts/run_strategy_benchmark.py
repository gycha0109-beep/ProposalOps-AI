#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from lib.gemini_generate_content import ProviderError, call_gemini_generate_content, get_gemini_api_key
from lib.strategy_eval import aggregate_strategy_evaluations, evaluate_strategy, parse_strategy_output


DEFAULT_CONFIG = "configs/proposal-strategist-benchmark-v1.json"


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
    markers = ["## Information classes", "## Prompt"]
    positions = [(content.find(marker), marker) for marker in markers if marker in content]
    if not positions:
        return content.strip()
    pos, _ = min(positions, key=lambda x: x[0])
    return content[pos:].strip()


def parse_versions(value, available):
    if value == "all":
        return list(available)
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in requested if item not in available]
    if unknown:
        raise SystemExit("Unknown prompt versions: " + ", ".join(unknown))
    return requested


def common_contract():
    return '''
## Benchmark Output Contract

Return JSON only. Do not use Markdown fences.

{"results":[{"rfp_id":"RFP-TEST-001","strategy":{"proposal_thesis":"...","concept":"...","strategy_pillars":[]}}]}

Rules:
- Return exactly one result per input rfp_id.
- Put the strategy object under `strategy`.
- Every strategy must contain `strategy_pillars` as an array.
- Other fields and pillar fields should follow the active prompt variant.
- Do not invent company facts, performance numbers, client names, or contract amounts absent from the supplied inputs.
'''


def build_batch(config, split_name):
    neutral = load_json(config["inputs_file"])
    neutral_by_id = {item["rfp_id"]: item for item in neutral["inputs"]}
    cases = []
    for case in config["cases"][split_name]:
        rfp_id = case["rfp_id"]
        if rfp_id not in neutral_by_id:
            raise SystemExit(f"Missing strategist neutral input: {rfp_id}")
        rfp_text = Path(case["rfp_file"]).read_text(encoding="utf-8")
        cases.append({
            "rfp_id": rfp_id,
            "rfp_text": rfp_text,
            "evidence_pack": neutral_by_id[rfp_id]["evidence_packs"],
        })
    return cases


def run_one(config, split_name, version, batch, api_key, commit):
    prompt_path = Path(config["versions"][version])
    prompt_content = prompt_path.read_text(encoding="utf-8")
    instructions = extract_prompt_body(prompt_content) + "\n\n" + common_contract()
    parameters = config["parameters"]

    response = call_gemini_generate_content(
        api_key=api_key,
        model=config["model"],
        thinking_level=parameters["thinking_level"],
        max_output_tokens=parameters["max_output_tokens"],
        system_instruction=instructions,
        input_text=json.dumps({"task":"Create proposal strategy for each case independently.","cases":batch}, ensure_ascii=False, indent=2),
        max_503_retries=int(parameters.get("max_503_retries", 1)),
        retry_delay_seconds=int(parameters.get("retry_delay_seconds", 15)),
    )

    raw_output = response["output_text"]
    parsed = parse_strategy_output(raw_output)
    rows = parsed.get("results", []) if parsed else []
    if not isinstance(rows, list):
        rows = []
    by_id = {row.get("rfp_id"): row for row in rows if isinstance(row, dict) and row.get("rfp_id")}

    neutral = load_json(config["inputs_file"])
    neutral_by_id = {item["rfp_id"]: item for item in neutral["inputs"]}
    per_rfp = []
    for case in config["cases"][split_name]:
        rfp_id = case["rfp_id"]
        row = by_id.get(rfp_id, {})
        strategy = row.get("strategy", row) if isinstance(row, dict) else {}
        gold = load_json(case["gold_file"])
        pack = {"evidence_packs": neutral_by_id[rfp_id]["evidence_packs"]}
        evaluation = evaluate_strategy(strategy if isinstance(strategy, dict) else {}, gold, pack)
        per_rfp.append({"rfp_id": rfp_id, "found": bool(row), "evaluation": evaluation})

    aggregate = aggregate_strategy_evaluations(per_rfp)
    aggregate["result_coverage"] = round(sum(row["found"] for row in per_rfp) / len(per_rfp), 4) if per_rfp else 0.0

    return {
        "run_id": f'proposal_strategist-{config["benchmark_version"]}-{split_name}-{version}-01',
        "track": "proposal_strategist",
        "benchmark_version": config["benchmark_version"],
        "split": split_name,
        "prompt_version": version,
        "prompt_file": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt_content.encode("utf-8")).hexdigest(),
        "model": response["model"],
        "parameters": {
            "thinking_level": parameters["thinking_level"],
            "max_output_tokens": parameters["max_output_tokens"],
            "max_503_retries": parameters.get("max_503_retries", 1),
            "retry_delay_seconds": parameters.get("retry_delay_seconds", 15),
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
        "json_parseable": parsed is not None,
        "raw_output": raw_output,
        "parsed_output": parsed,
        "evaluation": {"metrics": aggregate, "per_rfp": per_rfp},
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
    batch = build_batch(config, args.split)

    if args.split == "holdout" and not args.plan_only and not args.confirm_holdout:
        raise SystemExit("Holdout execution is protected. Freeze a candidate first.")

    plan = {
        "track": config["track"],
        "benchmark_version": config["benchmark_version"],
        "provider": config["provider"],
        "model": config["model"],
        "split": args.split,
        "rfp_count": len(batch),
        "prompt_versions": versions,
        "planned_calls": len(versions),
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    try:
        api_key = get_gemini_api_key()
    except ProviderError as exc:
        raise SystemExit(str(exc)) from exc

    commit = git_commit()
    root = Path(args.output_root or f'runs/proposal_strategist/{config["run_namespace"]}')
    completed = 0
    failed = 0
    for version in versions:
        path = root / args.split / version / "run-01.json"
        if path.exists() and not args.overwrite:
            print(f"SKIP existing: {path}")
            continue
        print(f"RUN {args.split} {version} rfps={len(batch)}")
        try:
            record = run_one(config, args.split, version, batch, api_key, commit)
        except ProviderError as exc:
            failure = root / args.split / "_failures" / f"{version}.json"
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_text(json.dumps({"timestamp_utc":datetime.now(timezone.utc).isoformat(),"prompt_version":version,"split":args.split,"error":str(exc),"git_commit":commit}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            failed += 1
            print(f"  FAILED: {exc}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        completed += 1
        m = record["evaluation"]["metrics"]
        print(f'  coverage={m["requirement_coverage"]} evidence={m["evidence_validity"]} unsupported={m["unsupported_company_claim_count"]}')

    print(f"completed={completed} failed={failed} planned={len(versions)}")
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

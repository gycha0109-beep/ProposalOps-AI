#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from lib.evidence_eval import evaluate_evidence_builder, load_corpus, parse_evidence_output
from lib.openai_responses import ProviderError, call_openai_responses, get_openai_api_key


DEFAULT_CONFIG = "configs/evidence-builder-benchmark-v1.json"


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_commit():
    github_sha = os.environ.get("GITHUB_SHA", "").strip()
    if github_sha:
        return github_sha
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def common_contract():
    return r'''
## Benchmark Output Contract

Return JSON only. Do not use Markdown fences.

{
  "results": [
    {
      "requirement_id": "R-201",
      "status": "SUPPORTED | PARTIAL_REFERENCE_ONLY | NO_REFERENCE_FOUND",
      "evidence": [
        {
          "evidence_id": "EV-R-201-01",
          "asset_id": "PA-...",
          "proposal_id": "PROP-...",
          "title": "exact candidate title",
          "supported_point": "what this source actually supports",
          "reusable_patterns": ["..."],
          "company_facts": [],
          "support_level": "direct | partial | pattern_only",
          "allowed_use": "REFERENCE_FACT | REFERENCE_PATTERN",
          "prohibited_use": "what must not be claimed from this evidence",
          "source": {
            "file_name": "exact source file",
            "page": 1,
            "source_type": "exact source type"
          }
        }
      ]
    }
  ]
}

Rules:
- Return exactly one result per supplied requirement_id.
- Evidence IDs must be sequential within each requirement: EV-{requirement_id}-01, -02, ...
- Do not select irrelevant candidates merely to fill a quota.
- If status is NO_REFERENCE_FOUND, evidence must be [].
'''


def build_batch(config: dict, gold: dict):
    retrieval = load_json(gold["source_retrieval_report"])
    rows = {}
    for split in ("dev", "holdout"):
        for row in retrieval.get(split, {}).get("cases", []):
            rows[row["case_id"]] = row

    rfp_run = load_json(config["rfp_analysis_run"])
    rfp = rfp_run["parsed_output"]
    requirements = {item["id"]: item for item in rfp.get("requirements", [])}

    corpus = load_corpus(config["corpus"])
    cases = []
    for case in gold["cases"]:
        retrieval_row = rows.get(case["retrieval_case_id"])
        if not retrieval_row:
            raise SystemExit(f'Missing retrieval case: {case["retrieval_case_id"]}')
        requirement = requirements.get(case["requirement_id"])
        if not requirement:
            raise SystemExit(f'Missing RFP requirement: {case["requirement_id"]}')

        candidates = []
        for rank, record in enumerate(retrieval_row.get("records", []), start=1):
            asset_id = record.get("asset_id")
            doc = corpus.get(asset_id)
            if not doc:
                raise SystemExit(f"Missing corpus asset: {asset_id}")
            candidates.append({
                "retrieval_rank": rank,
                "retrieval_score": record.get("score"),
                "asset_id": asset_id,
                "name": doc["name"],
                "text": doc["text"],
                "metadata": doc["metadata"],
            })

        cases.append({
            "requirement": requirement,
            "retrieval_query": retrieval_row["query"],
            "candidates": candidates,
        })
    return cases, corpus


def parse_versions(value: str, available: dict):
    if value == "all":
        return list(available)
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in requested if item not in available]
    if unknown:
        raise SystemExit("Unknown prompt versions: " + ", ".join(unknown))
    return requested


def run_one(config, version, cases, gold, corpus, api_key, commit):
    prompt_path = Path(config["versions"][version])
    prompt_content = prompt_path.read_text(encoding="utf-8")
    response = call_openai_responses(
        api_key=api_key,
        model=config["model"],
        reasoning_effort=config["parameters"]["reasoning_effort"],
        max_output_tokens=config["parameters"]["max_output_tokens"],
        instructions=prompt_content.strip() + "\n\n" + common_contract(),
        input_text=json.dumps({
            "task": "Build evidence packs for each requirement independently from the supplied retrieval candidates.",
            "rfp_id": gold["rfp_id"],
            "cases": cases,
        }, ensure_ascii=False, indent=2),
        max_retries=int(config["parameters"].get("max_retries", 2)),
        retry_delay_seconds=int(config["parameters"].get("retry_delay_seconds", 5)),
    )

    parsed = parse_evidence_output(response["output_text"])
    evaluation = evaluate_evidence_builder(parsed or {}, gold, corpus)
    return {
        "run_id": f'evidence-builder-{config["benchmark_version"]}-dev-{version}-01',
        "track": "evidence_builder",
        "benchmark_version": config["benchmark_version"],
        "split": "dev",
        "prompt_version": version,
        "prompt_file": str(prompt_path),
        "prompt_sha256": hashlib.sha256(prompt_content.encode("utf-8")).hexdigest(),
        "model": response["model"],
        "parameters": config["parameters"],
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": commit,
            "provider": response["provider"],
            "provider_response_id": response["response_id"],
            "latency_seconds": response["latency_seconds"],
            "retry_count": response.get("retry_count", 0),
            "usage": response.get("usage", {}),
        },
        "json_parseable": parsed is not None,
        "raw_output": response["output_text"],
        "parsed_output": parsed,
        "evaluation": evaluation,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--versions", default="all")
    parser.add_argument("--output-root")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    gold = load_json(config["gold_file"])
    versions = parse_versions(args.versions, config["versions"])
    cases, corpus = build_batch(config, gold)

    plan = {
        "track": config["track"],
        "benchmark_version": config["benchmark_version"],
        "provider": config["provider"],
        "model": config["model"],
        "rfp_id": gold["rfp_id"],
        "case_count": len(cases),
        "prompt_versions": versions,
        "planned_calls": len(versions),
        "retrieval_source": gold["source_retrieval_report"],
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

    root = Path(args.output_root or config["output_root"])
    commit = git_commit()
    failed = 0

    for version in versions:
        path = root / "dev" / version / "run-01.json"
        if path.exists() and not args.overwrite:
            print(f"SKIP existing: {path}")
            continue
        print(f"RUN dev {version} cases={len(cases)}")
        try:
            record = run_one(config, version, cases, gold, corpus, api_key, commit)
        except ProviderError as exc:
            failure = root / "dev" / "_failures" / f"{version}.json"
            failure.parent.mkdir(parents=True, exist_ok=True)
            failure.write_text(json.dumps({
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "prompt_version": version,
                "error": str(exc),
                "git_commit": commit,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"FAILED {version}: {exc}")
            failed += 1
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        metrics = record["evaluation"]["metrics"]
        print(json.dumps({
            "version": version,
            "pass": record["evaluation"]["pass"],
            "metrics": metrics,
        }, ensure_ascii=False))

    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_API_BASE = "https://api.dify.ai/v1"
PRODUCTION_NAME = "ProposalOps Production v1"
BENCHMARK_NAME = "ProposalOps Benchmark v1"


class DifyError(RuntimeError):
    pass


def request(api_base: str, api_key: str, method: str, path: str, payload: dict | None = None):
    body = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise DifyError(f"Dify HTTP {exc.code} {method} {path}: {raw}") from exc


def list_datasets(api_base: str, api_key: str) -> list[dict]:
    page = 1
    rows = []
    while True:
        response = request(
            api_base,
            api_key,
            "GET",
            f"/datasets?page={page}&limit=100",
        )
        rows.extend(response.get("data", []))
        if not response.get("has_more"):
            break
        page += 1
    return rows


def create_dataset(api_base: str, api_key: str, name: str, description: str) -> dict:
    return request(
        api_base,
        api_key,
        "POST",
        "/datasets",
        {
            "name": name,
            "description": description,
            "indexing_technique": "high_quality",
            "permission": "only_me",
            "provider": "vendor",
            "retrieval_model": {
                "search_method": "semantic_search",
                "reranking_enable": False,
                "top_k": 5,
                "score_threshold_enabled": False,
            },
        },
    )


def ensure_dataset(api_base: str, api_key: str, name: str, description: str, current: list[dict]):
    matches = [row for row in current if row.get("name") == name]
    if len(matches) > 1:
        raise DifyError(f"Multiple Dify datasets share the name: {name}")
    if matches:
        return matches[0], False
    created = create_dataset(api_base, api_key, name, description)
    return created, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.environ.get("DIFY_API_BASE") or DEFAULT_API_BASE)
    parser.add_argument("--api-key", default=os.environ.get("DIFY_API_KEY"))
    parser.add_argument("--out", default="runs/dify/datasets.json")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    plan = {
        "api_base": args.api_base,
        "api_key_configured": bool(args.api_key),
        "datasets": [
            {"role": "production", "name": PRODUCTION_NAME, "corpus": "51 normal assets"},
            {"role": "benchmark", "name": BENCHMARK_NAME, "corpus": "51 normal + 12 hard negatives"},
        ],
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if not args.api_key:
        raise SystemExit("DIFY_API_KEY or --api-key is required.")

    current = list_datasets(args.api_base, args.api_key)
    production, production_created = ensure_dataset(
        args.api_base,
        args.api_key,
        PRODUCTION_NAME,
        "ProposalOps AI production knowledge: 51 synthetic normal Proposal Assets.",
        current,
    )
    current.append(production)
    benchmark, benchmark_created = ensure_dataset(
        args.api_base,
        args.api_key,
        BENCHMARK_NAME,
        "ProposalOps AI retrieval benchmark: same 51 normal assets + 12 synthetic hard negatives as frozen lexical baseline.",
        current,
    )

    state = {
        "api_base": args.api_base,
        "production": {
            "name": PRODUCTION_NAME,
            "dataset_id": production["id"],
            "created": production_created,
        },
        "benchmark": {
            "name": BENCHMARK_NAME,
            "dataset_id": benchmark["id"],
            "created": benchmark_created,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

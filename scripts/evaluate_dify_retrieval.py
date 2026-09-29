#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_API_BASE = "https://api.dify.ai/v1"


class DifyError(RuntimeError):
    pass


def request(api_base: str, api_key: str, method: str, path: str, payload: dict):
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise DifyError(f"Dify HTTP {exc.code}: {body}") from exc


def asset_id_from_record(record: dict) -> str | None:
    segment = record.get("segment") or {}
    document = segment.get("document") or {}
    metadata = document.get("doc_metadata") or {}
    if isinstance(metadata, dict) and metadata.get("asset_id"):
        return str(metadata["asset_id"])

    name = str(document.get("name") or "")
    match = re.match(r"^(PA-[A-Z]+-\d+-P\d+)", name)
    if match:
        return match.group(1)

    content = str(segment.get("content") or "")
    match = re.search(r"asset_id:\s*(PA-[A-Z]+-\d+-P\d+)", content)
    return match.group(1) if match else None


def retrieve(api_base: str, api_key: str, dataset_id: str, query: str, top_k: int, search_method: str):
    payload = {
        "query": query,
        "retrieval_model": {
            "search_method": search_method,
            "reranking_enable": False,
            "top_k": top_k,
            "score_threshold_enabled": False,
        },
    }
    return request(api_base, api_key, "POST", f"/datasets/{dataset_id}/retrieve", payload)


def metrics(cases: list[dict]) -> dict:
    total = len(cases)
    hit1 = hit3 = hit5 = 0
    reciprocal = 0.0
    misses = []

    for row in cases:
        expected = set(row["expected_asset_ids"])
        ranked = row["retrieved_asset_ids"]
        rank = next((i + 1 for i, asset_id in enumerate(ranked) if asset_id in expected), None)
        hit1 += int(rank is not None and rank <= 1)
        hit3 += int(rank is not None and rank <= 3)
        hit5 += int(rank is not None and rank <= 5)
        reciprocal += 1.0 / rank if rank else 0.0
        if rank != 1:
            misses.append(
                {
                    "case_id": row["case_id"],
                    "rank": rank,
                    "wrong_top1": ranked[0] if ranked else None,
                    "expected": row["expected_asset_ids"],
                }
            )

    return {
        "cases": total,
        "hit_at_1": round(hit1 / total, 4) if total else 0,
        "hit_at_3": round(hit3 / total, 4) if total else 0,
        "hit_at_5": round(hit5 / total, 4) if total else 0,
        "mrr": round(reciprocal / total, 4) if total else 0,
        "top1_misses": misses,
    }


def load_cases(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_split(api_base, api_key, dataset_id, path, top_k, search_method):
    frozen = load_cases(path)
    rows = []
    for case in frozen["cases"]:
        response = retrieve(
            api_base,
            api_key,
            dataset_id,
            case["query"],
            top_k,
            search_method,
        )
        records = response.get("records", [])
        ranked = []
        raw = []
        for record in records:
            asset_id = asset_id_from_record(record)
            if asset_id and asset_id not in ranked:
                ranked.append(asset_id)
            raw.append(
                {
                    "asset_id": asset_id,
                    "score": record.get("score"),
                    "document_name": ((record.get("segment") or {}).get("document") or {}).get("name"),
                    "segment_id": (record.get("segment") or {}).get("id"),
                }
            )
        rows.append(
            {
                "case_id": case["id"],
                "query": case["query"],
                "expected_asset_ids": case["expected_asset_ids"],
                "retrieved_asset_ids": ranked,
                "records": raw,
            }
        )
        print(f"{case['id']}: {ranked[:5]}")

    return {
        "split": frozen["split"],
        "source": path,
        "metrics": metrics(rows),
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.environ.get("DIFY_API_BASE") or DEFAULT_API_BASE)
    parser.add_argument("--api-key", default=os.environ.get("DIFY_API_KEY"))
    parser.add_argument(
        "--dataset-id",
        default=os.environ.get("DIFY_BENCHMARK_DATASET_ID") or os.environ.get("DIFY_DATASET_ID"),
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--search-method",
        choices=("semantic_search", "full_text_search", "hybrid_search", "keyword_search"),
        default="semantic_search",
    )
    parser.add_argument("--dev", default="evals/frozen/v1/dev/retrieval.json")
    parser.add_argument("--holdout", default="evals/frozen/v1/holdout/retrieval.json")
    parser.add_argument("--baseline", default="evals/baselines/retrieval-v1.json")
    parser.add_argument("--out", default="reports/dify-retrieval-v1.json")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    plan = {
        "dataset_id_configured": bool(args.dataset_id),
        "api_key_configured": bool(args.api_key),
        "search_method": args.search_method,
        "top_k": args.top_k,
        "dev_cases": len(load_cases(args.dev)["cases"]),
        "holdout_cases": len(load_cases(args.holdout)["cases"]),
        "planned_retrieval_calls": len(load_cases(args.dev)["cases"]) + len(load_cases(args.holdout)["cases"]),
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if not args.dataset_id:
        raise SystemExit("DIFY_DATASET_ID or --dataset-id is required.")
    if not args.api_key:
        raise SystemExit("DIFY_API_KEY or --api-key is required.")

    dev = run_split(
        args.api_base, args.api_key, args.dataset_id, args.dev, args.top_k, args.search_method
    )
    holdout = run_split(
        args.api_base, args.api_key, args.dataset_id, args.holdout, args.top_k, args.search_method
    )
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))

    result = {
        "version": "1.0",
        "type": "dify_knowledge_retrieval",
        "dataset_id": args.dataset_id,
        "search_method": args.search_method,
        "top_k": args.top_k,
        "corpus": {
            "assets": 63,
            "hard_negatives_in_dify": 12,
        },
        "dev": dev,
        "holdout": holdout,
        "lexical_baseline": {
            "retriever": baseline["retriever"],
            "corpus": baseline["corpus"],
            "dev": baseline["dev"],
            "holdout": baseline["holdout"],
        },
        "comparison_note": (
            "Dify benchmark-v1 uses the same 51 normal assets + 12 hard negatives "
            "as the local lexical baseline for a like-for-like corpus comparison."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

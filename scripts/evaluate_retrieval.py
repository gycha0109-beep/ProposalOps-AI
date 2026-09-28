#!/usr/bin/env python3
"""Small, dependency-free lexical retrieval baseline for ProposalOps AI.

This is NOT the Dify retrieval result. It exists to make dataset regressions
visible before the assets are uploaded to the actual knowledge base.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
from pathlib import Path


TEXT_FIELDS = ("title", "project_type", "section", "normalized_text")
LIST_FIELDS = (
    "objective",
    "target_audience",
    "deliverables",
    "strategies",
    "differentiators",
    "channels",
    "kpis",
    "reusable_patterns",
    "tags",
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def flatten_asset(asset: dict) -> str:
    parts = [str(asset.get(key, "")) for key in TEXT_FIELDS]
    for key in LIST_FIELDS:
        parts.extend(str(value) for value in asset.get(key, []))
    return " ".join(parts).lower()


def tokens(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    compact = re.sub(r"\s", "", normalized)
    result: list[str] = []

    for n in (2, 3):
        result.extend(compact[i : i + n] for i in range(max(0, len(compact) - n + 1)))

    result.extend(re.findall(r"[a-z0-9]+|[가-힣]+", normalized))
    return result


def build_vector(counter: collections.Counter, df: collections.Counter, n_docs: int) -> dict[str, float]:
    vector: dict[str, float] = {}
    for term, tf in counter.items():
        idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
        vector[term] = (1 + math.log(tf)) * idf
    return vector


def cosine(query_vector: dict[str, float], doc_vector: dict[str, float]) -> float:
    dot = sum(value * doc_vector.get(term, 0.0) for term, value in query_vector.items())
    q_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    d_norm = math.sqrt(sum(value * value for value in doc_vector.values()))
    return dot / (q_norm * d_norm) if q_norm and d_norm else 0.0


def evaluate(assets: list[dict], gold: dict) -> dict:
    doc_counters = [collections.Counter(tokens(flatten_asset(asset))) for asset in assets]
    df: collections.Counter = collections.Counter()
    for counter in doc_counters:
        df.update(counter.keys())

    doc_vectors = [build_vector(counter, df, len(assets)) for counter in doc_counters]

    ranks: list[int | None] = []
    case_results: list[dict] = []

    for case in gold["cases"]:
        q_counter = collections.Counter(tokens(case["query"]))
        q_vector = build_vector(q_counter, df, len(assets))

        scored = sorted(
            (
                (cosine(q_vector, doc_vector), asset["asset_id"])
                for asset, doc_vector in zip(assets, doc_vectors)
            ),
            reverse=True,
        )

        expected = set(case["expected_asset_ids"])
        rank = next((index + 1 for index, (_, asset_id) in enumerate(scored) if asset_id in expected), None)
        ranks.append(rank)

        case_results.append(
            {
                "id": case["id"],
                "expected_asset_ids": case["expected_asset_ids"],
                "rank": rank,
                "top_results": [
                    {"asset_id": asset_id, "score": round(score, 6)}
                    for score, asset_id in scored[:5]
                ],
            }
        )

    total = len(ranks)

    def hit_at(k: int) -> float:
        return sum(rank is not None and rank <= k for rank in ranks) / total

    mrr = sum((1 / rank) if rank else 0 for rank in ranks) / total

    return {
        "retriever": "local_char_ngram_tfidf_baseline",
        "dataset_version": gold.get("version"),
        "asset_count": len(assets),
        "case_count": total,
        "metrics": {
            "hit_at_1": round(hit_at(1), 4),
            "hit_at_3": round(hit_at(3), 4),
            "hit_at_5": round(hit_at(5), 4),
            "mrr": round(mrr, 4),
        },
        "cases": case_results,
        "limitations": [
            "synthetic demo dataset",
            "small corpus",
            "lexical baseline only",
            "not a Dify Knowledge retrieval result",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", default="data/processed/proposals/proposal-assets.jsonl")
    parser.add_argument("--gold", default="evals/retrieval-goldset.json")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    assets = load_jsonl(Path(args.assets))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    result = evaluate(assets, gold)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()

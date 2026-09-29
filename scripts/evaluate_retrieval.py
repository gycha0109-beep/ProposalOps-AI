#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import math
import re
from pathlib import Path


TEXT_FIELDS = ("title", "project_type", "section", "normalized_text")
LIST_FIELDS = (
    "objective", "target_audience", "deliverables", "strategies",
    "differentiators", "channels", "kpis", "reusable_patterns", "tags",
)


def load_assets(path: Path) -> list[dict]:
    files = [path] if path.is_file() else sorted(path.rglob("*.jsonl"))
    assets = []
    for file in files:
        assets.extend(
            json.loads(line)
            for line in file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return assets


def flatten_asset(asset: dict) -> str:
    parts = [str(asset.get(key, "")) for key in TEXT_FIELDS]
    for key in LIST_FIELDS:
        parts.extend(str(value) for value in asset.get(key, []))
    return " ".join(parts).lower()


def tokens(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    compact = re.sub(r"\s", "", normalized)
    result = []
    for n in (2, 3):
        result.extend(compact[i:i+n] for i in range(max(0, len(compact) - n + 1)))
    result.extend(re.findall(r"[a-z0-9]+|[가-힣]+", normalized))
    return result


def vector(counter, df, n_docs):
    out = {}
    for term, tf in counter.items():
        idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
        out[term] = (1 + math.log(tf)) * idf
    return out


def cosine(a, b):
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    an = math.sqrt(sum(v*v for v in a.values()))
    bn = math.sqrt(sum(v*v for v in b.values()))
    return dot / (an * bn) if an and bn else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="data/processed/proposals")
    ap.add_argument("--gold", default="evals/frozen/v1/dev/retrieval.json")
    ap.add_argument("--out")
    args = ap.parse_args()

    assets = load_assets(Path(args.assets))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))

    counters = [collections.Counter(tokens(flatten_asset(a))) for a in assets]
    df = collections.Counter()
    for c in counters:
        df.update(c.keys())
    vectors = [vector(c, df, len(assets)) for c in counters]

    ranks = []
    cases = []
    for case in gold["cases"]:
        q = vector(collections.Counter(tokens(case["query"])), df, len(assets))
        scored = sorted(
            ((cosine(q, dv), asset["asset_id"]) for asset, dv in zip(assets, vectors)),
            reverse=True,
        )
        expected = set(case["expected_asset_ids"])
        rank = next((i + 1 for i, (_, aid) in enumerate(scored) if aid in expected), None)
        ranks.append(rank)
        cases.append({
            "id": case["id"],
            "rank": rank,
            "expected_asset_ids": case["expected_asset_ids"],
            "top_results": [
                {"asset_id": aid, "score": round(score, 6)}
                for score, aid in scored[:5]
            ],
        })

    total = len(ranks)
    hit = lambda k: sum(r is not None and r <= k for r in ranks) / total
    result = {
        "retriever": "local_char_ngram_tfidf_baseline",
        "split": gold.get("split"),
        "asset_count": len(assets),
        "case_count": total,
        "metrics": {
            "hit_at_1": round(hit(1), 4),
            "hit_at_3": round(hit(3), 4),
            "hit_at_5": round(hit(5), 4),
            "mrr": round(sum((1/r) if r else 0 for r in ranks) / total, 4),
        },
        "cases": cases,
        "limitations": [
            "synthetic benchmark",
            "lexical baseline only",
            "not a Dify retrieval result",
        ],
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_assets(path):
    path = Path(path)
    files = [path] if path.is_file() else sorted(path.rglob("*.jsonl"))
    assets = []
    for file in files:
        assets.extend(
            json.loads(line)
            for line in file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return assets


def bullets(values):
    return "\n".join(f"- {value}" for value in values) if values else "- 없음"


def render(asset):
    source = asset["source"]
    return f"""# {asset["title"]}

## Asset Identity
- asset_id: {asset["asset_id"]}
- proposal_id: {asset["proposal_id"]}
- category: {asset["category"]}
- client_type: {asset["client_type"]}
- project_type: {asset["project_type"]}
- page_type: {asset["page_type"]}
- source_file: {source["file_name"]}
- source_page: {source["page"]}
- reuse_level: {asset["reuse_level"]}

## Objective
{bullets(asset.get("objective", []))}

## Target Audience
{bullets(asset.get("target_audience", []))}

## Strategies
{bullets(asset.get("strategies", []))}

## Reusable Patterns
{bullets(asset.get("reusable_patterns", []))}

## KPI
{bullets(asset.get("kpis", []))}

## Retrieval Text
{asset.get("normalized_text", "")}

## Provenance
{source["file_name"]} / page {source["page"]}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="data/processed/proposals")
    ap.add_argument("--out-dir", default="data/knowledge/documents")
    ap.add_argument("--manifest", default="data/knowledge/metadata-manifest.csv")
    args = ap.parse_args()

    assets = load_assets(args.assets)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = Path(args.manifest)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for asset in assets:
        name = f'{asset["asset_id"]}.md'
        (out_dir / name).write_text(render(asset), encoding="utf-8")
        rows.append({
            "document_name": name,
            "asset_id": asset["asset_id"],
            "proposal_id": asset["proposal_id"],
            "category": asset["category"],
            "client_type": asset["client_type"],
            "page_type": asset["page_type"],
            "source_page": asset["source"]["page"],
            "reuse_level": asset["reuse_level"],
            "sensitivity": asset["sensitivity"],
        })

    with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"rendered={len(rows)}")


if __name__ == "__main__":
    main()

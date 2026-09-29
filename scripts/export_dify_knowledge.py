#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "exports" / "dify" / "knowledge-v1"


def source_paths(include_distractors: bool = False) -> list[Path]:
    paths = [ROOT / "data" / "processed" / "proposals" / "proposal-assets.jsonl"]
    paths.extend(sorted((ROOT / "data" / "processed" / "proposals" / "benchmark").glob("*.jsonl")))
    if include_distractors:
        paths.append(ROOT / "data" / "processed" / "proposals" / "distractors" / "hard-negatives.jsonl")
    return paths


def load_assets(include_distractors: bool = False) -> list[dict]:
    assets: list[dict] = []
    for path in source_paths(include_distractors):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                assets.append(json.loads(line))
    assets.sort(key=lambda item: item["asset_id"])
    return assets


def bullets(values) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- none"


def render_document(asset: dict) -> str:
    source = asset["source"]
    tags = asset.get("tags", [])
    return f"""# {asset["title"]}

## Provenance
- asset_id: {asset["asset_id"]}
- proposal_id: {asset["proposal_id"]}
- category: {asset["category"]}
- client_type: {asset["client_type"]}
- project_type: {asset["project_type"]}
- page: {asset["page"]}
- page_type: {asset["page_type"]}
- section: {asset["section"]}
- reuse_level: {asset["reuse_level"]}
- sensitivity: {asset["sensitivity"]}
- source_file: {source["file_name"]}
- source_page: {source["page"]}
- source_type: {source["source_type"]}
- tags: {", ".join(tags)}

## Normalized Summary
{asset["normalized_text"]}

## Objective
{bullets(asset.get("objective", []))}

## Target Audience
{bullets(asset.get("target_audience", []))}

## Deliverables
{bullets(asset.get("deliverables", []))}

## Strategies
{bullets(asset.get("strategies", []))}

## Differentiators
{bullets(asset.get("differentiators", []))}

## Channels
{bullets(asset.get("channels", []))}

## KPIs
{bullets(asset.get("kpis", []))}

## Reusable Patterns
{bullets(asset.get("reusable_patterns", []))}

## Company Facts
{bullets(asset.get("company_facts", []))}

## Search Terms
{", ".join(tags + asset.get("reusable_patterns", []) + asset.get("strategies", []))}
""".strip()


def native_metadata(asset: dict) -> dict:
    source = asset["source"]
    return {
        "asset_id": asset["asset_id"],
        "proposal_id": asset["proposal_id"],
        "category": asset["category"],
        "client_type": asset["client_type"],
        "project_type": asset["project_type"],
        "page": asset["page"],
        "page_type": asset["page_type"],
        "section": asset["section"],
        "reuse_level": asset["reuse_level"],
        "sensitivity": asset["sensitivity"],
        "source_file": source["file_name"],
        "source_page": source["page"],
        "source_type": source["source_type"],
        "tags": "|".join(asset.get("tags", [])),
    }


def make_document(asset: dict) -> dict:
    text = render_document(asset)
    name = f'{asset["asset_id"]}__{asset["title"]}'
    return {
        "name": name[:255],
        "asset_id": asset["asset_id"],
        "text": text,
        "metadata": native_metadata(asset),
    }


def metadata_schema() -> dict:
    return {
        "version": "1.0",
        "fields": [
            {"name": "asset_id", "type": "string"},
            {"name": "proposal_id", "type": "string"},
            {"name": "category", "type": "string"},
            {"name": "client_type", "type": "string"},
            {"name": "project_type", "type": "string"},
            {"name": "page", "type": "number"},
            {"name": "page_type", "type": "string"},
            {"name": "section", "type": "string"},
            {"name": "reuse_level", "type": "string"},
            {"name": "sensitivity", "type": "string"},
            {"name": "source_file", "type": "string"},
            {"name": "source_page", "type": "number"},
            {"name": "source_type", "type": "string"},
            {"name": "tags", "type": "string"},
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--include-distractors", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    assets = load_assets(args.include_distractors)
    documents = [make_document(asset) for asset in assets]
    expected_count = 63 if args.include_distractors else 51

    if len(documents) != expected_count:
        raise SystemExit(f"Expected {expected_count} proposal assets, got {len(documents)}")

    ids = [doc["asset_id"] for doc in documents]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate asset_id found in Dify export.")

    docs_path = out / "documents.jsonl"
    docs_path.write_text(
        "\n".join(json.dumps(doc, ensure_ascii=False) for doc in documents) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "version": "1.0",
        "format": "dify_create_by_text_manifest",
        "document_count": len(documents),
        "source_files": [str(path.relative_to(ROOT)) for path in source_paths(args.include_distractors)],
        "excluded_sources": [] if args.include_distractors else ["data/processed/proposals/distractors/"],
        "include_distractors": args.include_distractors,
        "one_asset_per_document": True,
        "document_name_rule": "{asset_id}__{title}",
        "categories": dict(sorted(Counter(asset["category"] for asset in assets).items())),
        "reuse_levels": dict(sorted(Counter(asset["reuse_level"] for asset in assets).items())),
        "sensitivities": dict(sorted(Counter(asset["sensitivity"] for asset in assets).items())),
        "native_metadata_optional": True,
        "provenance_embedded_in_text": True,
        "note": "Generated by scripts/export_dify_knowledge.py.",
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "metadata-schema.json").write_text(
        json.dumps(metadata_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

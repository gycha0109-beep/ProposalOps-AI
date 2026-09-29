#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


REQUIRED_METADATA = {
    "asset_id",
    "proposal_id",
    "category",
    "client_type",
    "project_type",
    "page",
    "page_type",
    "section",
    "reuse_level",
    "sensitivity",
    "source_file",
    "source_page",
    "source_type",
    "tags",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exports/dify/knowledge-v1")
    args = parser.parse_args()

    root = Path(args.root)
    docs = [
        json.loads(line)
        for line in (root / "documents.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((root / "metadata-schema.json").read_text(encoding="utf-8"))

    errors = []
    if len(docs) != 51:
        errors.append(f"document_count={len(docs)} expected=51")
    if manifest.get("document_count") != 51:
        errors.append("manifest document_count must be 51")

    ids = [doc.get("asset_id") for doc in docs]
    if len(ids) != len(set(ids)):
        errors.append("duplicate asset_id")

    for doc in docs:
        asset_id = doc.get("asset_id")
        if not asset_id or not asset_id.startswith("PA-"):
            errors.append(f"invalid asset_id: {asset_id}")
        if asset_id and asset_id.startswith("PA-DIST-"):
            errors.append(f"distractor leaked into export: {asset_id}")
        if not doc.get("name", "").startswith(asset_id or ""):
            errors.append(f"document name does not preserve asset_id: {asset_id}")
        if not doc.get("text", "").strip():
            errors.append(f"empty document text: {asset_id}")
        if "## Provenance" not in doc.get("text", ""):
            errors.append(f"missing provenance block: {asset_id}")
        if f"- asset_id: {asset_id}" not in doc.get("text", ""):
            errors.append(f"asset_id not embedded in text: {asset_id}")
        metadata = doc.get("metadata") or {}
        missing = REQUIRED_METADATA - set(metadata)
        if missing:
            errors.append(f"{asset_id} missing metadata: {sorted(missing)}")
        actual_hash = hashlib.sha256(doc.get("text", "").encode("utf-8")).hexdigest()
        if actual_hash != doc.get("text_sha256"):
            errors.append(f"text hash mismatch: {asset_id}")

    schema_names = {field["name"] for field in schema.get("fields", [])}
    if schema_names != REQUIRED_METADATA:
        errors.append(
            f"metadata schema mismatch missing={sorted(REQUIRED_METADATA-schema_names)} extra={sorted(schema_names-REQUIRED_METADATA)}"
        )

    result = {
        "status": "PASS" if not errors else "FAIL",
        "document_count": len(docs),
        "unique_asset_ids": len(set(ids)),
        "categories": dict(sorted(Counter(doc["metadata"]["category"] for doc in docs).items())),
        "distractor_count": sum(1 for value in ids if value and value.startswith("PA-DIST-")),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

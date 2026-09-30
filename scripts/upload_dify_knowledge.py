#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_API_BASE = "https://api.dify.ai/v1"
DEFAULT_MANIFEST = "exports/dify/knowledge-v1/documents.jsonl"
DEFAULT_SCHEMA = "exports/dify/knowledge-v1/metadata-schema.json"
ASSET_ID_RE = re.compile(r"asset_id:\s*(PA-[A-Z]+-\d+-P\d+)")
COMPACT_SEED_MARKER = "PROPOSALOPS_SANDBOX_COMPACT_CONTAINER"
PACK_SEPARATOR = "\n<<<PROPOSALOPS_ASSET_BOUNDARY_V1>>>\n"


class DifyError(RuntimeError):
    pass


class DifyClient:
    def __init__(self, api_base: str, api_key: str, timeout: int = 120, min_interval_seconds: float = 0.0):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0

    def request(self, method: str, path: str, payload: dict | None = None):
        if self.min_interval_seconds > 0 and self._last_request_at:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)
        body = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 ProposalOps-AI/1.0",
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                self._last_request_at = time.monotonic()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            self._last_request_at = time.monotonic()
            raw = exc.read().decode("utf-8", errors="replace")
            raise DifyError(f"Dify HTTP {exc.code} {method} {path}: {raw}") from exc
        except urllib.error.URLError as exc:
            self._last_request_at = time.monotonic()
            raise DifyError(f"Dify request failed {method} {path}: {exc}") from exc


def load_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_schema(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["fields"]


def list_all_documents(client: DifyClient, dataset_id: str) -> list[dict]:
    page = 1
    result = []
    while True:
        payload = client.request(
            "GET",
            f"/datasets/{dataset_id}/documents?page={page}&limit=100",
        )
        result.extend(payload.get("data", []))
        if not payload.get("has_more"):
            break
        page += 1
    return result


def list_all_segments(client: DifyClient, dataset_id: str, document_id: str) -> list[dict]:
    page = 1
    result = []
    while True:
        payload = client.request(
            "GET",
            f"/datasets/{dataset_id}/documents/{document_id}/segments?page={page}&limit=100",
        )
        result.extend(payload.get("data", []))
        if not payload.get("has_more"):
            break
        page += 1
    return result


def ensure_metadata_fields(client: DifyClient, dataset_id: str, schema: list[dict]) -> dict[str, dict]:
    current = client.request("GET", f"/datasets/{dataset_id}/metadata")
    items = current.get("doc_metadata", current.get("data", current if isinstance(current, list) else []))
    by_name = {item["name"]: item for item in items if isinstance(item, dict) and item.get("name")}

    for field in schema:
        if field["name"] in by_name:
            continue
        created = client.request(
            "POST",
            f"/datasets/{dataset_id}/metadata",
            {"name": field["name"], "type": field["type"]},
        )
        if isinstance(created, dict) and created.get("name"):
            by_name[created["name"]] = created

    refreshed = client.request("GET", f"/datasets/{dataset_id}/metadata")
    items = refreshed.get("doc_metadata", refreshed.get("data", refreshed if isinstance(refreshed, list) else []))
    return {item["name"]: item for item in items if isinstance(item, dict) and item.get("name")}


def create_document(client: DifyClient, dataset_id: str, doc: dict) -> dict:
    payload = {
        "name": doc["name"],
        "text": doc["text"],
        "indexing_technique": "high_quality",
        "doc_form": "text_model",
        "process_rule": {
            "mode": "custom",
            "rules": {
                "pre_processing_rules": [
                    {"id": "remove_extra_spaces", "enabled": True},
                    {"id": "remove_urls_emails", "enabled": False},
                ],
                "segmentation": {
                    "separator": "\n\n",
                    "max_tokens": 1024,
                    "chunk_overlap": 0,
                },
            },
        },
    }
    return client.request(
        "POST",
        f"/datasets/{dataset_id}/document/create-by-text",
        payload,
    )


def wait_for_document_ready(
    client: DifyClient,
    dataset_id: str,
    document_id: str,
    timeout_seconds: int = 600,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while True:
        document = client.request("GET", f"/datasets/{dataset_id}/documents/{document_id}")
        status = str(document.get("indexing_status") or document.get("display_status") or "").lower()
        if status in {"completed", "available"}:
            return document
        if status in {"error", "failed", "paused"} or document.get("error"):
            raise DifyError(f"Document indexing failed for {document_id}: {document}")
        if time.monotonic() >= deadline:
            raise DifyError(f"Timed out waiting for Dify document {document_id}; last status={status!r}")


def asset_id_from_segment(segment: dict) -> str | None:
    content = str(segment.get("content") or "")
    match = ASSET_ID_RE.search(content)
    return match.group(1) if match else None


def pack_documents(docs: list[dict]) -> str:
    return PACK_SEPARATOR.join(doc["text"].strip() for doc in docs)


def create_packed_document(
    client: DifyClient,
    dataset_id: str,
    document_name: str,
    docs: list[dict],
) -> dict:
    payload = {
        "name": document_name,
        "text": pack_documents(docs),
        "indexing_technique": "high_quality",
        "doc_form": "text_model",
        "process_rule": {
            "mode": "custom",
            "rules": {
                "pre_processing_rules": [
                    {"id": "remove_extra_spaces", "enabled": True},
                    {"id": "remove_urls_emails", "enabled": False},
                ],
                "segmentation": {
                    "separator": PACK_SEPARATOR,
                    "max_tokens": 2048,
                    "chunk_overlap": 0,
                },
            },
        },
    }
    return client.request(
        "POST",
        f"/datasets/{dataset_id}/document/create-by-text",
        payload,
    )


def upload_compact(
    client: DifyClient,
    dataset_id: str,
    docs: list[dict],
    document_name: str,
) -> dict:
    existing_documents = list_all_documents(client, dataset_id)
    matches = [row for row in existing_documents if row.get("name") == document_name]
    if len(matches) > 1:
        raise DifyError(f"Multiple Dify documents share the compact name: {document_name}")

    created_document = False
    if matches:
        document_id = matches[0]["id"]
    else:
        response = create_packed_document(client, dataset_id, document_name, docs)
        document = response.get("document") or {}
        document_id = document.get("id")
        if not document_id:
            raise DifyError(f"Create packed document response missing document.id: {response}")
        created_document = True

    wait_for_document_ready(client, dataset_id, document_id)
    segments = list_all_segments(client, dataset_id, document_id)

    requested_ids = {doc["asset_id"] for doc in docs}
    by_asset = {}
    duplicate_assets = []
    unknown_segments = []

    for segment in segments:
        asset_id = asset_id_from_segment(segment)
        if not asset_id:
            unknown_segments.append(
                {
                    "segment_id": segment.get("id"),
                    "content_prefix": str(segment.get("content") or "")[:160],
                }
            )
            continue
        if asset_id in by_asset:
            duplicate_assets.append(asset_id)
        by_asset[asset_id] = segment

    missing_assets = sorted(requested_ids - set(by_asset))
    extra_assets = sorted(set(by_asset) - requested_ids)

    if duplicate_assets or missing_assets or extra_assets or unknown_segments or len(segments) != len(docs):
        raise DifyError(
            "Packed document segmentation mismatch: "
            + json.dumps(
                {
                    "expected_segments": len(docs),
                    "actual_segments": len(segments),
                    "duplicate_assets": sorted(set(duplicate_assets)),
                    "missing_assets": missing_assets,
                    "extra_assets": extra_assets,
                    "unknown_segments": unknown_segments,
                },
                ensure_ascii=False,
            )
        )

    return {
        "dataset_id": dataset_id,
        "api_base": client.api_base,
        "sandbox_compact": True,
        "compact_strategy": "single_document_custom_separator",
        "compact_document_name": document_name,
        "compact_document_id": document_id,
        "compact_document_created": created_document,
        "requested_documents": len(docs),
        "available_documents": len(docs),
        "dify_document_count": 1,
        "segment_count": len(segments),
        "created_documents": 1 if created_document else 0,
        "failure_count": 0,
        "native_metadata_enabled": False,
        "documents": [
            {
                "asset_id": doc["asset_id"],
                "document_name": document_name,
                "document_id": document_id,
                "segment_id": by_asset[doc["asset_id"]].get("id"),
            }
            for doc in docs
        ],
        "failures": [],
    }


def sync_metadata(
    client: DifyClient,
    dataset_id: str,
    document_rows: list[tuple[str, dict]],
    metadata_fields: dict[str, dict],
):
    operations = []
    for document_id, doc in document_rows:
        metadata_list = []
        for name, value in doc["metadata"].items():
            field = metadata_fields.get(name)
            if not field or not field.get("id"):
                continue
            metadata_list.append(
                {
                    "id": field["id"],
                    "name": name,
                    "value": value,
                }
            )
        operations.append(
            {
                "document_id": document_id,
                "metadata_list": metadata_list,
                "partial_update": True,
            }
        )

    for start in range(0, len(operations), 20):
        client.request(
            "POST",
            f"/datasets/{dataset_id}/documents/metadata",
            {"operation_data": operations[start : start + 20]},
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--metadata-schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--api-base", default=os.environ.get("DIFY_API_BASE") or DEFAULT_API_BASE)
    parser.add_argument("--dataset-id", default=os.environ.get("DIFY_DATASET_ID"))
    parser.add_argument("--api-key", default=os.environ.get("DIFY_API_KEY"))
    parser.add_argument("--delay-seconds", type=float, default=7.0)
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--skip-native-metadata", action="store_true")
    parser.add_argument("--require-native-metadata", action="store_true")
    parser.add_argument("--sandbox-compact", action="store_true")
    parser.add_argument("--compact-document-name")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--state-out", default="runs/dify/knowledge-v1/upload-state.json")
    args = parser.parse_args()

    docs = load_jsonl(args.manifest)
    if args.max_documents:
        docs = docs[: args.max_documents]

    plan = {
        "dataset_id_configured": bool(args.dataset_id),
        "api_key_configured": bool(args.api_key),
        "api_base": args.api_base,
        "asset_count": len(docs),
        "sandbox_compact": args.sandbox_compact,
        "dify_document_count": 1 if args.sandbox_compact else len(docs),
        "one_asset_per_document": not args.sandbox_compact,
        "one_asset_per_segment": args.sandbox_compact,
        "native_metadata": False if args.sandbox_compact else not args.skip_native_metadata,
        "create_endpoint": "/datasets/{dataset_id}/document/create-by-text",
        "segment_endpoint": "automatic custom-separator segmentation during create-by-text",
        "retrieval_endpoint": "/datasets/{dataset_id}/retrieve",
        "delay_seconds": args.delay_seconds,
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if not args.dataset_id:
        raise SystemExit("DIFY_DATASET_ID or --dataset-id is required.")
    if not args.api_key:
        raise SystemExit("DIFY_API_KEY or --api-key is required.")
    if args.sandbox_compact and not args.compact_document_name:
        raise SystemExit("--compact-document-name is required with --sandbox-compact.")

    client = DifyClient(
        args.api_base,
        args.api_key,
        min_interval_seconds=args.delay_seconds,
    )

    if args.sandbox_compact:
        state = upload_compact(client, args.dataset_id, docs, args.compact_document_name)
        state_path = Path(args.state_out)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return

    existing = list_all_documents(client, args.dataset_id)
    by_name = {item.get("name"): item for item in existing if item.get("name")}

    metadata_fields = {}
    native_metadata_enabled = not args.skip_native_metadata
    if native_metadata_enabled:
        try:
            metadata_fields = ensure_metadata_fields(
                client,
                args.dataset_id,
                load_schema(args.metadata_schema),
            )
        except DifyError as exc:
            if args.require_native_metadata:
                raise
            native_metadata_enabled = False
            print(f"WARNING: native Dify metadata unavailable; continuing with embedded provenance only: {exc}")

    uploaded = []
    skipped = []
    failures = []

    for index, doc in enumerate(docs, start=1):
        if doc["name"] in by_name:
            document_id = by_name[doc["name"]]["id"]
            skipped.append({"asset_id": doc["asset_id"], "document_id": document_id})
            uploaded.append((document_id, doc))
            continue

        try:
            response = create_document(client, args.dataset_id, doc)
            document = response.get("document") or {}
            document_id = document.get("id")
            if not document_id:
                raise DifyError(f"Create response missing document.id: {response}")
            uploaded.append((document_id, doc))
            print(f"[{index}/{len(docs)}] uploaded {doc['asset_id']} -> {document_id}")
        except DifyError as exc:
            failures.append({"asset_id": doc["asset_id"], "error": str(exc)})
            print(f"[{index}/{len(docs)}] FAILED {doc['asset_id']}: {exc}")

    if native_metadata_enabled and metadata_fields and uploaded:
        try:
            sync_metadata(client, args.dataset_id, uploaded, metadata_fields)
        except DifyError as exc:
            if args.require_native_metadata:
                raise
            native_metadata_enabled = False
            print(f"WARNING: native metadata sync failed; documents remain usable via embedded provenance: {exc}")

    state = {
        "dataset_id": args.dataset_id,
        "api_base": args.api_base,
        "sandbox_compact": False,
        "requested_documents": len(docs),
        "available_documents": len(uploaded),
        "created_documents": len(uploaded) - len(skipped),
        "skipped_existing": len(skipped),
        "failure_count": len(failures),
        "native_metadata_enabled": native_metadata_enabled,
        "documents": [
            {
                "asset_id": doc["asset_id"],
                "document_name": doc["name"],
                "document_id": document_id,
            }
            for document_id, doc in uploaded
        ],
        "failures": failures,
    }
    state_path = Path(args.state_out)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))

    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

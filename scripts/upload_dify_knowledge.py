#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_API_BASE = "https://api.dify.ai/v1"
DEFAULT_MANIFEST = "exports/dify/knowledge-v1/documents.jsonl"
DEFAULT_SCHEMA = "exports/dify/knowledge-v1/metadata-schema.json"


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
            raw = exc.read().decode("utf-8", errors="replace")
            raise DifyError(f"Dify HTTP {exc.code} {method} {path}: {raw}") from exc
        except urllib.error.URLError as exc:
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
    parser.add_argument("--api-base", default=os.environ.get("DIFY_API_BASE", DEFAULT_API_BASE))
    parser.add_argument("--dataset-id", default=os.environ.get("DIFY_DATASET_ID"))
    parser.add_argument("--api-key", default=os.environ.get("DIFY_API_KEY"))
    parser.add_argument("--delay-seconds", type=float, default=7.0)
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--skip-native-metadata", action="store_true")
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
        "document_count": len(docs),
        "one_asset_per_document": True,
        "native_metadata": not args.skip_native_metadata,
        "create_endpoint": "/datasets/{dataset_id}/document/create-by-text",
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

    client = DifyClient(
        args.api_base,
        args.api_key,
        min_interval_seconds=args.delay_seconds,
    )
    existing = list_all_documents(client, args.dataset_id)
    by_name = {item.get("name"): item for item in existing if item.get("name")}

    metadata_fields = {}
    if not args.skip_native_metadata:
        metadata_fields = ensure_metadata_fields(
            client,
            args.dataset_id,
            load_schema(args.metadata_schema),
        )

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

    if not args.skip_native_metadata and uploaded:
        sync_metadata(client, args.dataset_id, uploaded, metadata_fields)

    state = {
        "dataset_id": args.dataset_id,
        "api_base": args.api_base,
        "requested_documents": len(docs),
        "available_documents": len(uploaded),
        "created_documents": len(uploaded) - len(skipped),
        "skipped_existing": len(skipped),
        "failure_count": len(failures),
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

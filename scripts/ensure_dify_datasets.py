#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_API_BASE = "https://api.dify.ai/v1"
PRODUCTION_NAME = "ProposalOps Production v1"
BENCHMARK_NAME = "ProposalOps Benchmark v1"


class DifyError(RuntimeError):
    pass


class DifyClient:
    def __init__(self, api_base: str, api_key: str, timeout: int = 120, min_interval_seconds: float = 7.0):
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


def list_datasets(client: DifyClient) -> list[dict]:
    page = 1
    rows = []
    while True:
        response = client.request("GET", f"/datasets?page={page}&limit=100")
        rows.extend(response.get("data", []))
        if not response.get("has_more"):
            break
        page += 1
    return rows


def create_dataset(client: DifyClient, name: str, description: str) -> dict:
    return client.request(
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


def ensure_dataset(client: DifyClient, name: str, description: str, current: list[dict]):
    matches = [row for row in current if row.get("name") == name]
    if len(matches) > 1:
        raise DifyError(f"Multiple Dify datasets share the name: {name}")
    if matches:
        return matches[0], False
    created = create_dataset(client, name, description)
    return created, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.environ.get("DIFY_API_BASE") or DEFAULT_API_BASE)
    parser.add_argument("--api-key", default=os.environ.get("DIFY_API_KEY"))
    parser.add_argument("--delay-seconds", type=float, default=7.0)
    parser.add_argument("--out", default="runs/dify/datasets.json")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    plan = {
        "api_base": args.api_base,
        "api_key_configured": bool(args.api_key),
        "delay_seconds": args.delay_seconds,
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

    client = DifyClient(args.api_base, args.api_key, min_interval_seconds=args.delay_seconds)
    current = list_datasets(client)
    production, production_created = ensure_dataset(
        client,
        PRODUCTION_NAME,
        "ProposalOps AI production knowledge: 51 synthetic normal Proposal Assets, packed as asset-level chunks for Dify Sandbox.",
        current,
    )
    current.append(production)
    benchmark, benchmark_created = ensure_dataset(
        client,
        BENCHMARK_NAME,
        "ProposalOps AI retrieval benchmark: same 51 normal assets + 12 synthetic hard negatives as frozen lexical baseline, packed as asset-level chunks for Dify Sandbox.",
        current,
    )

    state = {
        "api_base": args.api_base,
        "sandbox_compact": True,
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

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request


DEFAULT_API_BASE = "https://api.dify.ai/v1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 ProposalOps-AI/1.0"
ASSET_ID_RE = re.compile(r"asset_id:\s*(PA-[A-Z]+-(?:\d+-)?P\d+)")


class DifyError(RuntimeError):
    pass


class DifyKnowledgeClient:
    def __init__(
        self,
        api_key: str,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = 120,
        min_interval_seconds: float = 7.0,
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
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
            "User-Agent": USER_AGENT,
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                self._last_request_at = time.monotonic()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            self._last_request_at = time.monotonic()
            response_body = exc.read().decode("utf-8", errors="replace")
            raise DifyError(
                f"Dify HTTP {exc.code} {method} {path}: {response_body}"
            ) from exc
        except urllib.error.URLError as exc:
            self._last_request_at = time.monotonic()
            raise DifyError(f"Dify request failed {method} {path}: {exc}") from exc

    def retrieve(
        self,
        dataset_id: str,
        query: str,
        *,
        top_k: int = 5,
        search_method: str = "semantic_search",
    ):
        return self.request(
            "POST",
            f"/datasets/{dataset_id}/retrieve",
            {
                "query": query,
                "retrieval_model": {
                    "search_method": search_method,
                    "reranking_enable": False,
                    "top_k": top_k,
                    "score_threshold_enabled": False,
                },
            },
        )


def asset_id_from_record(record: dict) -> str | None:
    segment = record.get("segment") or {}
    document = segment.get("document") or {}
    metadata = document.get("doc_metadata") or {}
    if isinstance(metadata, dict) and metadata.get("asset_id"):
        return str(metadata["asset_id"])

    name = str(document.get("name") or "")
    match = re.match(r"^(PA-[A-Z]+-(?:\d+-)?P\d+)", name)
    if match:
        return match.group(1)

    content = str(segment.get("content") or "")
    match = ASSET_ID_RE.search(content)
    return match.group(1) if match else None

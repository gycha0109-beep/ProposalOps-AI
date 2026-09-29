from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


API_URL = "https://api.openai.com/v1/responses"


class ProviderError(RuntimeError):
    pass


def _extract_output_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str) and response["output_text"].strip():
        return response["output_text"].strip()

    texts = []
    for item in response.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    return "\n".join(texts).strip()


def call_openai_responses(
    *,
    api_key: str,
    model: str,
    reasoning_effort: str,
    max_output_tokens: int,
    instructions: str,
    input_text: str,
    timeout_seconds: int = 180,
    max_retries: int = 2,
    retry_delay_seconds: int = 5,
) -> dict:
    payload = {
        "model": model,
        "reasoning": {"effort": reasoning_effort},
        "instructions": instructions,
        "input": input_text,
        "max_output_tokens": max_output_tokens,
        "store": False,
    }

    started = time.perf_counter()
    retries = 0

    while True:
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = response.status
                body = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 500, 502, 503, 504) and retries < max_retries:
                retries += 1
                time.sleep(retry_delay_seconds * retries)
                continue
            raise ProviderError(f"OpenAI HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            if retries < max_retries:
                retries += 1
                time.sleep(retry_delay_seconds * retries)
                continue
            raise ProviderError(f"OpenAI request failed: {exc}") from exc

    elapsed = time.perf_counter() - started
    data = json.loads(body)
    output_text = _extract_output_text(data)
    if not output_text:
        raise ProviderError(
            "OpenAI response did not contain output text. "
            f"status={data.get('status')} error={data.get('error')}"
        )

    usage = data.get("usage") or {}
    return {
        "provider": "openai",
        "response_id": data.get("id"),
        "model": data.get("model", model),
        "status": status,
        "latency_seconds": round(elapsed, 4),
        "retry_count": retries,
        "usage": usage,
        "output_text": output_text,
        "raw_response": data,
    }


def get_openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ProviderError(
            "OPENAI_API_KEY is required for live runs. "
            "Use --plan-only to validate without calling a model."
        )
    return key

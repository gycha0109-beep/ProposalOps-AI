from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class ProviderError(RuntimeError):
    pass


def _extract_output_text(response: dict) -> str:
    texts = []
    for candidate in response.get("candidates", []):
        content = candidate.get("content") or {}
        for part in content.get("parts", []):
            if part.get("thought") is True:
                continue
            text = part.get("text")
            if isinstance(text, str):
                texts.append(text)
    return "\n".join(texts).strip()


def _normalize_usage(response: dict) -> dict:
    usage = response.get("usageMetadata") or {}
    return {
        "input_tokens": usage.get("promptTokenCount"),
        "output_tokens": usage.get("candidatesTokenCount")
            if usage.get("candidatesTokenCount") is not None
            else usage.get("responseTokenCount"),
        "total_tokens": usage.get("totalTokenCount"),
        "output_tokens_details": {
            "reasoning_tokens": usage.get("thoughtsTokenCount")
        },
        "provider_usage_metadata": usage,
    }


def call_gemini_generate_content(
    *,
    api_key: str,
    model: str,
    thinking_level: str,
    max_output_tokens: int,
    system_instruction: str,
    input_text: str,
    timeout_seconds: int = 180,
) -> dict:
    model_path = urllib.parse.quote(model, safe="-._")
    url = f"{API_BASE}/{model_path}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": input_text}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "thinkingConfig": {
                "thinkingLevel": thinking_level,
            },
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderError(f"Gemini HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Gemini request failed: {exc}") from exc

    elapsed = time.perf_counter() - started
    data = json.loads(body)
    output_text = _extract_output_text(data)

    if not output_text:
        finish_reasons = [
            candidate.get("finishReason")
            for candidate in data.get("candidates", [])
        ]
        raise ProviderError(
            "Gemini response did not contain output text. "
            f"finish_reasons={finish_reasons}"
        )

    return {
        "provider": "gemini",
        "response_id": data.get("responseId"),
        "model": data.get("modelVersion", model),
        "status": status,
        "latency_seconds": round(elapsed, 4),
        "usage": _normalize_usage(data),
        "output_text": output_text,
        "raw_response": data,
    }


def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ProviderError(
            "GEMINI_API_KEY is required for live runs. "
            "Use --plan-only to validate the benchmark without calling a model."
        )
    return key

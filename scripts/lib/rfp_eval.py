from __future__ import annotations

import json
import re
from typing import Any


UNKNOWN_TERMS = (
    "unknown",
    "미기재",
    "미명시",
    "명시하지 않",
    "확인 불가",
    "알 수 없",
    "없음",
)


def parse_json_output(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(r"^\`\`\`(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\`\`\`$", "", text)

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None

    return value if isinstance(value, dict) else None


def _get_path(obj: dict[str, Any], path: str) -> Any:
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _blob(value: Any) -> str:
    if isinstance(value, str):
        return value.lower()
    return json.dumps(value, ensure_ascii=False).lower()


def _normalize_semantic_text(value: Any) -> str:
    text = _blob(value)
    replacements = {
        "계약체결일": "계약일",
        "계약 체결일": "계약일",
        "개월간": "개월",
        "개월 간": "개월",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"[\\s·ㆍ→$\\\\()\[\]{}:;,./_-]+", "", text)


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _contains_all(blob: str, terms: list[str]) -> bool:
    return all(term.lower() in blob for term in terms)


def _value_or_raw(parsed: dict | None, path: str, raw_text: str) -> Any:
    if parsed is not None:
        value = _get_path(parsed, path)
        if not _is_missing(value):
            return value
    return raw_text


def _parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
            return float(cleaned)
    return None


def _evaluation_items(parsed: dict) -> list:
    items = parsed.get("evaluation")
    if not isinstance(items, list):
        items = parsed.get("evaluations", [])
    return items if isinstance(items, list) else []


def _evaluation_scores(parsed: dict) -> list[float]:
    items = _evaluation_items(parsed)
    scores = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("score", "points", "weight", "배점"):
            if key in item:
                number = _parse_number(item.get(key))
                if number is not None:
                    scores.append(number)
                break
    return scores


def _grounding_metrics(parsed: dict | None, source_text: str | None) -> dict:
    if parsed is None:
        return {
            "source_quote_coverage": 0.0,
            "source_quote_validity": None,
            "groundable_item_count": 0,
            "source_quote_count": 0,
        }

    items = []
    for key in ("scope", "deliverables", "requirements", "evaluation", "evaluations", "constraints"):
        values = parsed.get(key, [])
        if isinstance(values, list):
            items.extend(values)

    if not items:
        return {
            "source_quote_coverage": 0.0,
            "source_quote_validity": None,
            "groundable_item_count": 0,
            "source_quote_count": 0,
        }

    quote_count = 0
    valid_count = 0
    source_normalized = re.sub(r"\s+", " ", source_text or "").strip().lower()

    for item in items:
        if not isinstance(item, dict):
            continue
        quote = item.get("source_quote")
        if not isinstance(quote, str) or not quote.strip():
            continue
        quote_count += 1
        quote_normalized = re.sub(r"\s+", " ", quote).strip().lower()
        if source_text is not None and quote_normalized in source_normalized:
            valid_count += 1

    coverage = quote_count / len(items)
    validity = (valid_count / quote_count) if quote_count else None

    return {
        "source_quote_coverage": round(coverage, 4),
        "source_quote_validity": round(validity, 4) if validity is not None else None,
        "groundable_item_count": len(items),
        "source_quote_count": quote_count,
    }


def _evaluate_case(case: dict, raw_text: str, parsed: dict | None) -> tuple[bool, dict]:
    metric = case["metric"]
    raw_blob = raw_text.lower()
    detail: dict[str, Any] = {"id": case["id"], "metric": metric}

    if metric == "exact_or_semantic":
        expected = _normalize_semantic_text(case["expected"])
        actual_source = _value_or_raw(parsed, case["path"], raw_text)
        actual = _normalize_semantic_text(actual_source)
        ok = expected in actual
        detail["expected"] = case["expected"]
        detail["evaluated_source"] = (
            case["path"]
            if parsed is not None and not _is_missing(_get_path(parsed, case["path"]))
            else "raw_output_fallback"
        )
        return ok, detail

    if metric == "contains":
        terms = case["expected_terms"]
        actual_source = _value_or_raw(parsed, case["path"], raw_text)
        ok = _contains_all(_blob(actual_source), terms)
        detail["expected_terms"] = terms
        detail["evaluated_source"] = (
            case["path"]
            if parsed is not None and not _is_missing(_get_path(parsed, case["path"]))
            else "raw_output_fallback"
        )
        return ok, detail

    if metric == "deliverable":
        expected = case["expected"]
        if parsed is not None:
            blob = _blob(parsed.get("deliverables", []))
        else:
            blob = raw_blob
        ok = (
            expected["name_contains"].lower() in blob
            and expected["quantity"].lower() in blob
        )
        detail["expected"] = expected
        return ok, detail

    if metric == "evaluation_sum":
        if parsed is None:
            detail["reason"] = "unstructured output cannot be safely summed"
            return False, detail

        numeric_scores = _evaluation_scores(parsed)
        ok = bool(numeric_scores) and sum(numeric_scores) == float(case["expected"])
        detail["actual_sum"] = sum(numeric_scores) if numeric_scores else None
        detail["expected_sum"] = case["expected"]
        return ok, detail

    if metric == "unknown":
        if parsed is not None:
            value = _get_path(parsed, case["path"])
            if not _is_missing(value):
                ok = str(value).lower() == str(case["expected"]).lower()
                detail["actual"] = value
                return ok, detail

        if "budget" in case["path"]:
            has_budget_context = (
                "예산" in raw_text
                or "사업비" in raw_text
                or "budget" in raw_blob
            )
            has_unknown_marker = any(term in raw_blob for term in UNKNOWN_TERMS)
            ok = has_budget_context and has_unknown_marker
        else:
            ok = any(term in raw_blob for term in UNKNOWN_TERMS)
        detail["expected"] = case["expected"]
        return ok, detail

    if metric == "requirement_terms":
        terms = case["expected_terms"]
        blob = _blob(parsed.get("requirements", [])) if parsed is not None else raw_blob
        ok = _contains_all(blob, terms)
        detail["expected_terms"] = terms
        return ok, detail

    if metric == "requirement_present":
        term = case["expected_term"].lower()
        blob = _blob(parsed.get("requirements", [])) if parsed is not None else raw_blob
        ok = term in blob
        detail["expected_term"] = case["expected_term"]
        return ok, detail

    if metric == "unsupported_addition":
        hits = [
            term
            for term in case["forbidden_terms"]
            if term.lower() in raw_blob
        ]
        detail["forbidden_hits"] = hits
        return not hits, detail

    detail["reason"] = "unsupported metric"
    return False, detail


def evaluate_rfp(raw_text: str, gold: dict, source_text: str | None = None) -> dict:
    parsed = parse_json_output(raw_text)
    grounding = _grounding_metrics(parsed, source_text)

    details = []
    category_results: dict[str, list[bool]] = {
        "deliverable": [],
        "numeric": [],
        "requirement": [],
        "unsupported": [],
    }

    unsupported_hits = 0

    for case in gold["cases"]:
        ok, detail = _evaluate_case(case, raw_text, parsed)
        detail["pass"] = ok
        detail["critical"] = case.get("critical", False)
        details.append(detail)

        metric = case["metric"]
        if metric == "deliverable":
            category_results["deliverable"].append(ok)
            category_results["numeric"].append(ok)
        elif metric == "evaluation_sum":
            category_results["numeric"].append(ok)
        elif metric == "exact_or_semantic" and (
            "duration" in case.get("path", "") or "budget" in case.get("path", "")
        ):
            category_results["numeric"].append(ok)
        elif metric in ("requirement_terms", "requirement_present"):
            category_results["requirement"].append(ok)
        elif metric == "unsupported_addition":
            category_results["unsupported"].append(ok)
            unsupported_hits += len(detail.get("forbidden_hits", []))

    passed = sum(item["pass"] for item in details)
    total = len(details)

    def rate(name: str) -> float | None:
        values = category_results[name]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    output_truncated = (
        parsed is None
        and (
            raw_text.lstrip().startswith("```json")
            or raw_text.count("{") > raw_text.count("}")
            or raw_text.count("[") > raw_text.count("]")
        )
    )

    return {
        "track": "rfp_analyzer",
        "evaluator_version": "1.4",
        "gold_version": gold.get("version"),
        "split": gold.get("split"),
        "json_parseable": parsed is not None,
        "output_truncated": output_truncated,
        "metrics": {
            "assertion_pass_rate": round(passed / total, 4) if total else 0.0,
            "deliverable_recall": rate("deliverable"),
            "numeric_fidelity": rate("numeric"),
            "requirement_assertion_recall": rate("requirement"),
            "unsupported_addition_count": unsupported_hits,
            "source_quote_coverage": grounding["source_quote_coverage"],
            "source_quote_validity": grounding["source_quote_validity"],
        },
        "grounding": grounding,
        "passed": passed,
        "total": total,
        "details": details,
    }

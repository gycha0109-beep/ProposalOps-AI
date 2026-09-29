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


def _contains_all(blob: str, terms: list[str]) -> bool:
    return all(term.lower() in blob for term in terms)


def _evaluate_case(case: dict, raw_text: str, parsed: dict | None) -> tuple[bool, dict]:
    metric = case["metric"]
    raw_blob = raw_text.lower()
    detail: dict[str, Any] = {"id": case["id"], "metric": metric}

    if metric == "exact_or_semantic":
        expected = _normalize_semantic_text(case["expected"])
        if parsed is not None:
            value = _get_path(parsed, case["path"])
            actual = _normalize_semantic_text(value)
        else:
            actual = _normalize_semantic_text(raw_text)
        ok = expected in actual
        detail["expected"] = case["expected"]
        return ok, detail

    if metric == "contains":
        terms = case["expected_terms"]
        if parsed is not None:
            value = _get_path(parsed, case["path"])
            ok = _contains_all(_blob(value), terms)
        else:
            ok = _contains_all(raw_blob, terms)
        detail["expected_terms"] = terms
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

        scores = [
            item.get("score")
            for item in parsed.get("evaluation", [])
            if isinstance(item, dict)
        ]
        numeric_scores = [score for score in scores if isinstance(score, (int, float))]
        ok = bool(numeric_scores) and sum(numeric_scores) == case["expected"]
        detail["actual_sum"] = sum(numeric_scores) if numeric_scores else None
        detail["expected_sum"] = case["expected"]
        return ok, detail

    if metric == "unknown":
        if parsed is not None:
            value = _get_path(parsed, case["path"])
            ok = value == case["expected"]
            detail["actual"] = value
            return ok, detail

        if "budget" in case["path"]:
            has_budget_context = "예산" in raw_text or "사업비" in raw_text
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


def evaluate_rfp(raw_text: str, gold: dict) -> dict:
    parsed = parse_json_output(raw_text)

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

    return {
        "track": "rfp_analyzer",
        "evaluator_version": "1.1",
        "gold_version": gold.get("version"),
        "split": gold.get("split"),
        "json_parseable": parsed is not None,
        "metrics": {
            "assertion_pass_rate": round(passed / total, 4) if total else 0.0,
            "deliverable_recall": rate("deliverable"),
            "numeric_fidelity": rate("numeric"),
            "requirement_assertion_recall": rate("requirement"),
            "unsupported_addition_count": unsupported_hits,
        },
        "passed": passed,
        "total": total,
        "details": details,
    }

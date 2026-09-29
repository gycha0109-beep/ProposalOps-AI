from __future__ import annotations

import json
import re
from typing import Any


REQ_KEYS = ("rfp_requirement_ids", "related_requirement_ids", "requirement_ids")
EVIDENCE_KEYS = ("evidence_ids", "used_reference_ids", "evidence_asset_ids", "reference_ids")


def parse_strategy_output(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^\`\`\`(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*\`\`\`$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def evidence_map(pack):
    mapping = {}
    for group in pack.get("evidence_packs", []):
        for ev in group.get("evidence", []):
            if ev.get("evidence_id") and ev.get("asset_id"):
                mapping[ev["evidence_id"]] = ev["asset_id"]
    return mapping


def pillar_requirements(pillar):
    values = []
    for key in REQ_KEYS:
        item = pillar.get(key, [])
        if isinstance(item, list):
            values.extend(item)
    return values


def pillar_evidence(pillar):
    values = []
    for key in EVIDENCE_KEYS:
        item = pillar.get(key, [])
        if isinstance(item, list):
            values.extend(item)
    return values


def evaluate_strategy(strategy, gold, pack):
    serialized = json.dumps(strategy, ensure_ascii=False).lower()
    required = gold["required_requirement_ids"]
    covered = [rid for rid in required if rid.lower() in serialized]
    pillars = strategy.get("strategy_pillars", []) if isinstance(strategy, dict) else []
    if not isinstance(pillars, list):
        pillars = []

    emap = evidence_map(pack)
    valid_asset_ids = set(emap.values())
    citation_count = 0
    valid_evidence_count = 0
    evidence_details = []
    invalid_refs = []

    for expectation in gold["evidence_expectations"]:
        rid = expectation["requirement_id"]
        allowed = set(expectation["allowed_asset_ids"])
        cited = []
        for pillar in pillars:
            if not isinstance(pillar, dict):
                continue
            if rid in pillar_requirements(pillar):
                cited.extend(pillar_evidence(pillar))
        resolved = {emap.get(x, x) for x in cited}
        has_citation = bool(cited)
        is_valid = bool(resolved & allowed)
        citation_count += int(has_citation)
        valid_evidence_count += int(is_valid)
        for ref in cited:
            resolved_ref = emap.get(ref, ref)
            if resolved_ref not in valid_asset_ids:
                invalid_refs.append(ref)
        evidence_details.append({
            "requirement_id": rid,
            "cited_ids": cited,
            "resolved_assets": sorted(resolved),
            "allowed_assets": sorted(allowed),
            "citation_present": has_citation,
            "valid": is_valid,
        })

    forbidden_hits = [claim for claim in gold.get("forbidden_claims", []) if claim.lower() in serialized]
    quantitative_hits = [claim for claim in forbidden_hits if re.search(r"\d|%|원|만|억|년", claim)]
    info_classes = gold.get("required_information_classes", [])
    info_ok = all(item.lower() in serialized for item in info_classes)

    expected_evidence = len(gold["evidence_expectations"])
    return {
        "metrics": {
            "requirement_coverage": round(len(covered) / len(required), 4) if required else 0.0,
            "evidence_citation_coverage": round(citation_count / expected_evidence, 4) if expected_evidence else 0.0,
            "evidence_validity": round(valid_evidence_count / expected_evidence, 4) if expected_evidence else 0.0,
            "unsupported_company_claim_count": len(forbidden_hits),
            "unsupported_quantitative_claim_count": len(quantitative_hits),
            "information_class_separation": 1.0 if info_ok else 0.0,
            "invalid_evidence_reference_count": len(set(invalid_refs)),
        },
        "covered_requirement_ids": covered,
        "missing_requirement_ids": [rid for rid in required if rid not in covered],
        "forbidden_claim_hits": forbidden_hits,
        "invalid_evidence_refs": sorted(set(invalid_refs)),
        "evidence_details": evidence_details,
    }


def aggregate_strategy_evaluations(per_rfp):
    metric_names = [
        "requirement_coverage",
        "evidence_citation_coverage",
        "evidence_validity",
        "unsupported_company_claim_count",
        "unsupported_quantitative_claim_count",
        "information_class_separation",
        "invalid_evidence_reference_count",
    ]
    metrics = {}
    for name in metric_names:
        values = [row["evaluation"]["metrics"][name] for row in per_rfp]
        metrics[name] = round(sum(values) / len(values), 4) if values else None
    return metrics

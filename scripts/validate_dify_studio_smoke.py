#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lib.pagination_eval import validate_pagination
from lib.slide_eval import validate_slides
from lib.visual_eval import validate_visuals


NORMAL_REQUIRED = {
    "rfp_analysis",
    "evidence_packs",
    "proposal_strategy",
    "pagination",
    "slides",
    "visuals",
    "qa",
}


def parse_maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def unwrap_outputs(payload: dict) -> dict:
    if isinstance(payload.get("data"), dict) and isinstance(
        payload["data"].get("outputs"), dict
    ):
        return payload["data"]["outputs"]
    if isinstance(payload.get("outputs"), dict):
        return payload["outputs"]
    return payload


def normalize_outputs(payload: dict) -> dict:
    outputs = unwrap_outputs(payload)
    return {key: parse_maybe_json(value) for key, value in outputs.items()}


def provenance_summary(
    *,
    evidence_packs: list[dict],
    strategy: dict,
    pagination: dict,
    slides: dict,
    visuals: dict,
) -> dict:
    evidence_index = {}
    for pack in evidence_packs:
        requirement_id = pack.get("requirement_id")
        for evidence in pack.get("evidence", []) or []:
            evidence_id = evidence.get("evidence_id")
            if evidence_id:
                evidence_index[evidence_id] = {
                    "requirement_id": requirement_id,
                    "asset_id": evidence.get("asset_id"),
                }

    strategy_ids = {
        item.get("strategy_id")
        for item in strategy.get("strategy_pillars", []) or []
        if item.get("strategy_id")
    }
    slide_ids = {
        item.get("page_id")
        for item in slides.get("slides", []) or []
        if item.get("page_id")
    }
    visual_ids = {
        item.get("page_id")
        for item in visuals.get("visuals", []) or []
        if item.get("page_id")
    }

    chains = []
    broken = []
    for page in pagination.get("pages", []) or []:
        page_id = page.get("page_id")
        for requirement_id in page.get("rfp_requirement_ids", []) or []:
            for strategy_id in page.get("strategy_ids", []) or []:
                evidence_ids = [
                    evidence_id
                    for evidence_id in page.get("evidence_ids", []) or []
                    if evidence_index.get(evidence_id, {}).get("requirement_id")
                    == requirement_id
                ] or [None]

                for evidence_id in evidence_ids:
                    evidence = evidence_index.get(evidence_id) if evidence_id else None
                    valid = bool(
                        strategy_id in strategy_ids
                        and page_id in slide_ids
                        and page_id in visual_ids
                        and (evidence_id is None or evidence)
                    )
                    row = {
                        "requirement_id": requirement_id,
                        "asset_id": evidence.get("asset_id") if evidence else None,
                        "evidence_id": evidence_id,
                        "strategy_id": strategy_id,
                        "page_id": page_id,
                        "valid": valid,
                    }
                    chains.append(row)
                    if not valid:
                        broken.append(row)

    return {
        "pass": not broken,
        "chain_count": len(chains),
        "broken_chains": broken,
    }


def validate_smoke(outputs: dict, *, expect_pages: int | None, page_limit: int) -> dict:
    missing = sorted(NORMAL_REQUIRED - set(outputs))
    if missing:
        return {
            "status": "FAIL",
            "errors": [{"code": "MISSING_OUTPUT", "keys": missing}],
        }

    rfp_analysis = outputs["rfp_analysis"]
    evidence_packs = outputs["evidence_packs"]
    proposal_strategy = outputs["proposal_strategy"]
    pagination = outputs["pagination"]
    slides = outputs["slides"]
    visuals = outputs["visuals"]
    qa = outputs["qa"]

    type_errors = []
    for name, value, expected in (
        ("rfp_analysis", rfp_analysis, dict),
        ("evidence_packs", evidence_packs, list),
        ("proposal_strategy", proposal_strategy, dict),
        ("pagination", pagination, dict),
        ("slides", slides, dict),
        ("visuals", visuals, dict),
        ("qa", qa, dict),
    ):
        if not isinstance(value, expected):
            type_errors.append(
                {
                    "code": "OUTPUT_TYPE",
                    "output": name,
                    "expected": expected.__name__,
                    "actual": type(value).__name__,
                }
            )
    if type_errors:
        return {"status": "FAIL", "errors": type_errors}

    coverage = validate_pagination(
        pagination,
        rfp_analysis,
        proposal_strategy,
        evidence_packs,
        page_limit=page_limit,
    )
    slide_gate = validate_slides(
        slides,
        pagination,
        rfp_analysis,
        evidence_packs,
    )
    visual_gate = validate_visuals(
        visuals,
        slides,
        pagination,
    )
    provenance = provenance_summary(
        evidence_packs=evidence_packs,
        strategy=proposal_strategy,
        pagination=pagination,
        slides=slides,
        visuals=visuals,
    )

    errors = []
    if coverage.get("status") != "PASS":
        errors.append(
            {
                "code": "COVERAGE_GATE_FAIL",
                "details": coverage.get("blocking_errors", []),
            }
        )
    if slide_gate.get("status") != "PASS":
        errors.append(
            {
                "code": "SLIDE_GATE_FAIL",
                "details": slide_gate.get("blocking_errors", []),
            }
        )
    if visual_gate.get("status") != "PASS":
        errors.append(
            {
                "code": "VISUAL_GATE_FAIL",
                "details": visual_gate.get("blocking_errors", []),
            }
        )
    if qa.get("status") != "PASS" or (qa.get("issues") or []):
        errors.append(
            {
                "code": "QA_FAIL",
                "qa_status": qa.get("status"),
                "issues": qa.get("issues", []),
            }
        )
    if not provenance["pass"]:
        errors.append(
            {
                "code": "BROKEN_PROVENANCE",
                "details": provenance["broken_chains"],
            }
        )

    page_count = len(pagination.get("pages", []) or [])
    slide_count = len(slides.get("slides", []) or [])
    visual_count = len(visuals.get("visuals", []) or [])
    if expect_pages is not None and (
        page_count != expect_pages
        or slide_count != expect_pages
        or visual_count != expect_pages
    ):
        errors.append(
            {
                "code": "EXPECTED_PAGE_COUNT_MISMATCH",
                "expected": expect_pages,
                "pages": page_count,
                "slides": slide_count,
                "visuals": visual_count,
            }
        )

    source_gate_statuses = {}
    for key in (
        "coverage_validation",
        "slide_validation",
        "visual_validation",
        "repair_validation",
    ):
        if key not in outputs:
            continue
        value = parse_maybe_json(outputs[key])
        if isinstance(value, dict):
            source_gate_statuses[key] = value.get("status")
            if value.get("status") not in (None, "PASS"):
                errors.append(
                    {
                        "code": "STUDIO_REPORTED_GATE_FAIL",
                        "gate": key,
                        "details": value,
                    }
                )

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "summary": {
            "pages": page_count,
            "slides": slide_count,
            "visuals": visual_count,
            "qa_status": qa.get("status"),
            "qa_issues": len(qa.get("issues", []) or []),
            "coverage_gate": coverage.get("status"),
            "slide_gate": slide_gate.get("status"),
            "visual_gate": visual_gate.get("status"),
            "broken_provenance_chains": len(provenance["broken_chains"]),
            "provenance_chains": provenance["chain_count"],
            "studio_reported_gates": source_gate_statuses,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a Dify Studio Phase 4 workflow execution response."
    )
    parser.add_argument("result_json")
    parser.add_argument("--expect-pages", type=int)
    parser.add_argument("--page-limit", type=int, default=8)
    args = parser.parse_args()

    payload = json.loads(Path(args.result_json).read_text(encoding="utf-8"))
    outputs = normalize_outputs(payload)
    result = validate_smoke(
        outputs,
        expect_pages=args.expect_pages,
        page_limit=args.page_limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    main()

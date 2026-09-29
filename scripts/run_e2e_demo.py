#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from lib.openai_responses import call_openai_responses, get_openai_api_key


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_json(raw):
    text = raw.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def prompt_text(path):
    content = Path(path).read_text(encoding="utf-8")
    if "## Prompt" in content:
        return content.split("## Prompt", 1)[1].strip()
    return content.strip()


def normalize_strategy(strategy):
    value = json.loads(json.dumps(strategy, ensure_ascii=False))
    for index, pillar in enumerate(value.get("strategy_pillars", []), start=1):
        pillar.setdefault("strategy_id", f"ST-{index:02d}")
    return value


def select_strategy(run, rfp_id):
    for row in (run.get("parsed_output") or {}).get("results", []):
        if row.get("rfp_id") == rfp_id:
            return normalize_strategy(row.get("strategy", row))
    raise RuntimeError(f"Strategy result not found for {rfp_id}")


def select_evidence(inputs, rfp_id):
    for item in inputs.get("inputs", []):
        if item.get("rfp_id") == rfp_id:
            return item.get("evidence_packs", [])
    raise RuntimeError(f"Evidence pack not found for {rfp_id}")


def call_stage(api_key, config, stage, instructions, payload):
    response = call_openai_responses(
        api_key=api_key,
        model=config["model"],
        reasoning_effort=config["reasoning_effort"],
        max_output_tokens=config["max_output_tokens"][stage],
        instructions=instructions,
        input_text=json.dumps(payload, ensure_ascii=False, indent=2),
        max_retries=2,
        retry_delay_seconds=5,
    )
    return parse_json(response["output_text"]), {
        "provider": response["provider"],
        "response_id": response["response_id"],
        "model": response["model"],
        "latency_seconds": response["latency_seconds"],
        "retry_count": response.get("retry_count", 0),
        "usage": response.get("usage", {}),
    }


def evidence_ids(evidence_packs):
    return {
        ev["evidence_id"]
        for pack in evidence_packs
        for ev in pack.get("evidence", [])
        if ev.get("evidence_id")
    }


def validate_pagination(pagination, rfp, strategy, evidence_packs):
    pages = pagination.get("pages", [])
    requirements = {item["id"] for item in rfp.get("requirements", [])}
    strategies = {
        item.get("strategy_id")
        for item in strategy.get("strategy_pillars", [])
        if item.get("strategy_id")
    }
    evidences = evidence_ids(evidence_packs)
    covered = set()
    invalid_req = set()
    invalid_strategy = set()
    invalid_evidence = set()

    for page in pages:
        for value in page.get("rfp_requirement_ids", []):
            if value in requirements:
                covered.add(value)
            else:
                invalid_req.add(value)
        for value in page.get("strategy_ids", []):
            if value not in strategies:
                invalid_strategy.add(value)
        for value in page.get("evidence_ids", []):
            if value not in evidences:
                invalid_evidence.add(value)

    errors = []
    ids = [p.get("page_id") for p in pages]
    numbers = [p.get("page_no") for p in pages]
    if not pages:
        errors.append("NO_PAGES")
    if len(ids) != len(set(ids)):
        errors.append("DUPLICATE_PAGE_ID")
    if numbers != list(range(1, len(pages) + 1)):
        errors.append("NON_SEQUENTIAL_PAGE_NO")
    if requirements - covered:
        errors.append("MISSING_REQUIREMENTS")
    if invalid_req:
        errors.append("INVALID_REQUIREMENT_ID")
    if invalid_strategy:
        errors.append("INVALID_STRATEGY_ID")
    if invalid_evidence:
        errors.append("INVALID_EVIDENCE_ID")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "page_count": len(pages),
        "missing_requirement_ids": sorted(requirements - covered),
        "invalid_requirement_ids": sorted(invalid_req),
        "invalid_strategy_ids": sorted(invalid_strategy),
        "invalid_evidence_ids": sorted(invalid_evidence),
    }


def validate_slides(slides_payload, pagination, evidence_packs):
    slides = slides_payload.get("slides", [])
    expected = {page["page_id"] for page in pagination.get("pages", [])}
    actual = {slide.get("page_id") for slide in slides}
    valid_evidence = evidence_ids(evidence_packs)
    invalid = set()
    for slide in slides:
        for value in slide.get("evidence_ids", []):
            if value not in valid_evidence:
                invalid.add(value)
        for block in slide.get("body_blocks", []):
            for value in block.get("evidence_ids", []):
                if value not in valid_evidence:
                    invalid.add(value)
    errors = []
    if expected != actual:
        errors.append("SLIDE_PAGE_COVERAGE_MISMATCH")
    if invalid:
        errors.append("INVALID_EVIDENCE_ID")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "missing_page_ids": sorted(expected - actual),
        "unexpected_page_ids": sorted(actual - expected),
        "invalid_evidence_ids": sorted(invalid),
    }


def validate_visuals(visuals_payload, slides_payload):
    expected = {slide.get("page_id") for slide in slides_payload.get("slides", [])}
    actual = {visual.get("page_id") for visual in visuals_payload.get("visuals", [])}
    errors = [] if expected == actual else ["VISUAL_PAGE_COVERAGE_MISMATCH"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "missing_page_ids": sorted(expected - actual),
        "unexpected_page_ids": sorted(actual - expected),
    }


def usage_summary(stage_meta):
    total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0}
    for meta in stage_meta.values():
        usage = meta.get("usage") or {}
        total["input_tokens"] += usage.get("input_tokens") or 0
        total["output_tokens"] += usage.get("output_tokens") or 0
        total["total_tokens"] += usage.get("total_tokens") or 0
        details = usage.get("output_tokens_details") or {}
        total["reasoning_tokens"] += details.get("reasoning_tokens") or 0
    return total


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/e2e-demo-v1.json")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    source = config["source"]
    root = Path(config["output_root"])

    if args.plan_only:
        print(json.dumps({
            "demo_id": config["demo_id"],
            "model": config["model"],
            "reasoning_effort": config["reasoning_effort"],
            "reused_validated_stages": ["rfp_analyzer", "proposal_strategist", "evidence_pack"],
            "live_stages": ["pagination", "slide_batch", "visual_batch", "proposal_qa"],
            "planned_calls": 4,
            "output_root": str(root),
        }, ensure_ascii=False, indent=2))
        return

    if root.exists() and any(root.iterdir()) and not args.overwrite:
        raise SystemExit(f"Output already exists: {root}. Use --overwrite.")

    root.mkdir(parents=True, exist_ok=True)
    api_key = get_openai_api_key()
    rfp_run = load_json(source["rfp_analysis_run"])
    strategist_run = load_json(source["strategist_run"])
    inputs = load_json(source["strategist_inputs"])

    rfp_id = source["rfp_id"]
    rfp = rfp_run["parsed_output"]
    strategy = select_strategy(strategist_run, rfp_id)
    evidence = select_evidence(inputs, rfp_id)
    meta = {}

    pagination_prompt = prompt_text(config["prompts"]["pagination"]) + f"""

Demo constraints:
- Use at most {config["default_page_limit"]} pages.
- Use only supplied requirement IDs, strategy IDs, and evidence IDs.
- Return the Pagination Planner JSON contract only.
"""
    pagination, meta["pagination"] = call_stage(
        api_key, config, "pagination", pagination_prompt,
        {
            "rfp_id": rfp_id,
            "rfp_analysis": rfp,
            "proposal_strategy": strategy,
            "evidence_packs": evidence,
            "page_limit": config["default_page_limit"],
        },
    )
    pagination_check = validate_pagination(pagination, rfp, strategy, evidence)
    if pagination_check["status"] != "PASS":
        write_json(root / "pagination-failed.json", {"output": pagination, "validation": pagination_check})
        raise SystemExit("Pagination deterministic validation failed.")

    slide_prompt = prompt_text(config["prompts"]["slide_draft"]) + """

Batch output contract:
Return JSON only as {"slides":[...]}.
Return exactly one slide object for every input page_id.
Each slide object must use the Slide Draft schema.
"""
    slides, meta["slides"] = call_stage(
        api_key, config, "slides", slide_prompt,
        {
            "rfp_id": rfp_id,
            "rfp_analysis": rfp,
            "proposal_strategy": strategy,
            "evidence_packs": evidence,
            "pages": pagination["pages"],
        },
    )
    slide_check = validate_slides(slides, pagination, evidence)
    if slide_check["status"] != "PASS":
        write_json(root / "slides-failed.json", {"output": slides, "validation": slide_check})
        raise SystemExit("Slide deterministic validation failed.")

    visual_prompt = prompt_text(config["prompts"]["visual_prompt"]) + """

Batch output contract:
Return JSON only as {"visuals":[...]}.
Return exactly one visual object for every slide page_id.
Each visual object must use the Visual Prompt schema.
"""
    visuals, meta["visuals"] = call_stage(
        api_key, config, "visuals", visual_prompt,
        {
            "rfp_id": rfp_id,
            "slides": slides["slides"],
            "pages": pagination["pages"],
            "evidence_packs": evidence,
        },
    )
    visual_check = validate_visuals(visuals, slides)
    if visual_check["status"] != "PASS":
        write_json(root / "visuals-failed.json", {"output": visuals, "validation": visual_check})
        raise SystemExit("Visual deterministic validation failed.")

    qa_prompt = prompt_text(config["prompts"]["proposal_qa"]) + """

Final package output contract:
Return JSON only:
{
  "status": "PASS | FAIL",
  "issues": [
    {
      "error_type": "MISSING_REQUIREMENT | UNSUPPORTED_CLAIM | INVALID_REFERENCE | CROSS_PROPOSAL_MERGE | STRATEGY_PAGE_MISMATCH | DUPLICATE_MESSAGE | OVERLONG_SLIDE",
      "severity": "BLOCK | WARN | INFO",
      "page_id": "PAGE-001 | null",
      "reason": "string",
      "suggested_action": "string"
    }
  ],
  "summary": "string"
}
If there is no real issue, return PASS with an empty issues array.
"""
    qa, meta["qa"] = call_stage(
        api_key, config, "qa", qa_prompt,
        {
            "rfp_id": rfp_id,
            "rfp_analysis": rfp,
            "evidence_packs": evidence,
            "proposal_strategy": strategy,
            "pagination": pagination,
            "slides": slides,
            "visuals": visuals,
            "deterministic_validations": {
                "pagination": pagination_check,
                "slides": slide_check,
                "visuals": visual_check,
            },
        },
    )

    package = {
        "demo_id": config["demo_id"],
        "rfp_id": rfp_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": config["model"],
        "reasoning_effort": config["reasoning_effort"],
        "source_runs": {
            "rfp_analysis": source["rfp_analysis_run"],
            "proposal_strategy": source["strategist_run"],
        },
        "rfp_analysis": rfp,
        "evidence_packs": evidence,
        "proposal_strategy": strategy,
        "pagination": pagination,
        "slides": slides,
        "visuals": visuals,
        "qa": qa,
        "deterministic_validations": {
            "pagination": pagination_check,
            "slides": slide_check,
            "visuals": visual_check,
        },
        "stage_metadata": meta,
        "usage": usage_summary(meta),
        "status": qa.get("status", "UNKNOWN"),
    }

    write_json(root / "pagination.json", pagination)
    write_json(root / "slides.json", slides)
    write_json(root / "visuals.json", visuals)
    write_json(root / "qa.json", qa)
    write_json(root / "final-package.json", package)

    print(json.dumps({
        "demo_id": config["demo_id"],
        "status": package["status"],
        "page_count": len(pagination.get("pages", [])),
        "slide_count": len(slides.get("slides", [])),
        "visual_count": len(visuals.get("visuals", [])),
        "qa_issue_count": len(qa.get("issues", [])),
        "usage": package["usage"],
        "output_root": str(root),
    }, ensure_ascii=False, indent=2))

    if package["status"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lib.openai_responses import call_openai_responses, get_openai_api_key


ROOT = Path("runs/e2e-demo/RFP-TEST-002")
PACKAGE = ROOT / "final-package-repaired.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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


def call(api_key, model, instructions, payload, max_output_tokens):
    response = call_openai_responses(
        api_key=api_key,
        model=model,
        reasoning_effort="low",
        max_output_tokens=max_output_tokens,
        instructions=instructions,
        input_text=json.dumps(payload, ensure_ascii=False, indent=2),
        max_retries=2,
        retry_delay_seconds=5,
    )
    return parse_json(response["output_text"]), {
        "response_id": response["response_id"],
        "model": response["model"],
        "latency_seconds": response["latency_seconds"],
        "retry_count": response.get("retry_count", 0),
        "usage": response.get("usage", {}),
    }


def main():
    package = load(PACKAGE)
    if package.get("status") == "PASS":
        print("Package already passed QA.")
        return

    issues = package.get("qa", {}).get("issues", [])
    affected_pages = {
        issue.get("page_id")
        for issue in issues
        if issue.get("page_id")
    }
    if not affected_pages:
        raise SystemExit("No page-scoped QA issues to repair.")

    page_by_id = {
        page["page_id"]: page
        for page in package["pagination"].get("pages", [])
    }
    slide_by_id = {
        slide["page_id"]: slide
        for slide in package["slides"].get("slides", [])
    }
    visual_by_id = {
        visual["page_id"]: visual
        for visual in package["visuals"].get("visuals", [])
    }
    strategy_by_id = {
        pillar["strategy_id"]: pillar
        for pillar in package["proposal_strategy"].get("strategy_pillars", [])
        if pillar.get("strategy_id")
    }

    affected_strategy_ids = set()
    for page_id in affected_pages:
        affected_strategy_ids.update(page_by_id[page_id].get("strategy_ids", []))

    affected_requirements = {
        req_id
        for page_id in affected_pages
        for req_id in page_by_id[page_id].get("rfp_requirement_ids", [])
    }
    relevant_evidence = [
        pack
        for pack in package.get("evidence_packs", [])
        if pack.get("requirement_id") in affected_requirements
    ]

    repair_prompt = prompt_text("prompts/production/targeted_repair.md") + """

This repair must follow the provenance chain upstream to downstream.
Repair only supplied strategy_ids and page_ids. Do not modify unaffected strategy pillars or pages.

Return JSON only:
{
  "strategy_repairs": [
    {
      "strategy_id": "ST-01",
      "repaired_pillar": { ...complete strategy pillar... }
    }
  ],
  "page_repairs": [
    {
      "page_id": "PAGE-001",
      "repaired_page": { ...complete pagination page... },
      "repaired_slide": { ...complete slide draft... },
      "repaired_visual": { ...complete visual prompt... }
    }
  ],
  "repair_summary": [
    {
      "error_type": "string",
      "target_id": "ST-01 or PAGE-001",
      "change": "string",
      "resolved": true
    }
  ],
  "escalation_required": false,
  "escalation_reason": null
}

Strict evidence rules:
- REFERENCE_PATTERN text may say only what cited supported_point/reusable_patterns directly entail.
- Do not add an operational step because it sounds reasonable.
- If an idea is useful but not directly supported, classify it as AI_RECOMMENDATION and remove reference evidence IDs from that idea.
- Preserve existing strategy_id, page_id, requirement IDs and valid evidence IDs.
- Do not invent new evidence IDs.
- Keep all RFP_FACT values exactly grounded in the supplied RFP.
- Every clause must be checked independently for entailment.

Specific QA guidance:
- R-205 evidence supports: 게시 전 변경정보 확인/재검수, 변경 시 기존 게시물 상태 갱신, 버전 표시. It does not directly support 제작 시점 검수 or an already-defined official 담당자/channel workflow.
- R-206 evidence supports: 도달, 상세조회, 저장, 지도/코스/예약 페이지 이동 and stage-based KPI. It does not directly support a 시청 stage or content-type/motivation/creator comparison axes unless those are clearly marked AI_RECOMMENDATION without evidence.
"""

    api_key = get_openai_api_key()
    model = package.get("model", "gpt-5.6-luna")

    repair, repair_meta = call(
        api_key,
        model,
        repair_prompt,
        {
            "qa_issues": issues,
            "affected_strategy_pillars": {
                sid: strategy_by_id[sid]
                for sid in affected_strategy_ids
                if sid in strategy_by_id
            },
            "affected_pages": {
                page_id: page_by_id[page_id]
                for page_id in affected_pages
            },
            "affected_slides": {
                page_id: slide_by_id[page_id]
                for page_id in affected_pages
            },
            "affected_visuals": {
                page_id: visual_by_id[page_id]
                for page_id in affected_pages
            },
            "relevant_evidence_packs": relevant_evidence,
            "rfp_analysis": package["rfp_analysis"],
        },
        7000,
    )

    merged_strategy = json.loads(json.dumps(package["proposal_strategy"], ensure_ascii=False))
    merged_pagination = json.loads(json.dumps(package["pagination"], ensure_ascii=False))
    merged_slides = json.loads(json.dumps(package["slides"], ensure_ascii=False))
    merged_visuals = json.loads(json.dumps(package["visuals"], ensure_ascii=False))

    strategy_index = {
        pillar["strategy_id"]: index
        for index, pillar in enumerate(merged_strategy.get("strategy_pillars", []))
        if pillar.get("strategy_id")
    }
    page_index = {
        page["page_id"]: index
        for index, page in enumerate(merged_pagination.get("pages", []))
    }
    slide_index = {
        slide["page_id"]: index
        for index, slide in enumerate(merged_slides.get("slides", []))
    }
    visual_index = {
        visual["page_id"]: index
        for index, visual in enumerate(merged_visuals.get("visuals", []))
    }

    for item in repair.get("strategy_repairs", []):
        strategy_id = item.get("strategy_id")
        repaired = item.get("repaired_pillar")
        if strategy_id not in affected_strategy_ids:
            raise SystemExit(f"Repair attempted unaffected strategy: {strategy_id}")
        if not isinstance(repaired, dict) or repaired.get("strategy_id") != strategy_id:
            raise SystemExit(f"Invalid strategy repair: {strategy_id}")
        merged_strategy["strategy_pillars"][strategy_index[strategy_id]] = repaired

    for item in repair.get("page_repairs", []):
        page_id = item.get("page_id")
        if page_id not in affected_pages:
            raise SystemExit(f"Repair attempted unaffected page: {page_id}")
        repaired_page = item.get("repaired_page")
        repaired_slide = item.get("repaired_slide")
        repaired_visual = item.get("repaired_visual")
        if not isinstance(repaired_page, dict) or repaired_page.get("page_id") != page_id:
            raise SystemExit(f"Invalid page repair: {page_id}")
        if not isinstance(repaired_slide, dict) or repaired_slide.get("page_id") != page_id:
            raise SystemExit(f"Invalid slide repair: {page_id}")
        if not isinstance(repaired_visual, dict) or repaired_visual.get("page_id") != page_id:
            raise SystemExit(f"Invalid visual repair: {page_id}")
        merged_pagination["pages"][page_index[page_id]] = repaired_page
        merged_slides["slides"][slide_index[page_id]] = repaired_slide
        merged_visuals["visuals"][visual_index[page_id]] = repaired_visual

    qa_prompt = prompt_text("prompts/production/proposal_qa.md") + """

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

    qa, qa_meta = call(
        api_key,
        model,
        qa_prompt,
        {
            "rfp_id": package["rfp_id"],
            "rfp_analysis": package["rfp_analysis"],
            "evidence_packs": package["evidence_packs"],
            "proposal_strategy": merged_strategy,
            "pagination": merged_pagination,
            "slides": merged_slides,
            "visuals": merged_visuals,
            "previous_qa_issues": issues,
            "chain_repair_output": repair,
        },
        6000,
    )

    cycle = len(package.get("repair_history", [])) + 1
    current = {
        "cycle": cycle,
        "scope": "strategy_to_visual",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repair_output": repair,
        "stage_metadata": {
            "repair": repair_meta,
            "qa_recheck": qa_meta,
        },
    }

    repaired_package = json.loads(json.dumps(package, ensure_ascii=False))
    repaired_package["proposal_strategy"] = merged_strategy
    repaired_package["pagination"] = merged_pagination
    repaired_package["slides"] = merged_slides
    repaired_package["visuals"] = merged_visuals
    repaired_package["qa"] = qa
    repaired_package["status"] = qa.get("status", "UNKNOWN")
    history = list(package.get("repair_history", []))
    repaired_package["repair_history"] = history + [current]
    repaired_package["repair"] = current

    save(ROOT / f"repair-cycle-{cycle}.json", repair)
    save(ROOT / f"strategy-repaired-cycle-{cycle}.json", merged_strategy)
    save(ROOT / f"pagination-repaired-cycle-{cycle}.json", merged_pagination)
    save(ROOT / f"slides-repaired-cycle-{cycle}.json", merged_slides)
    save(ROOT / f"visuals-repaired-cycle-{cycle}.json", merged_visuals)
    save(ROOT / f"qa-recheck-cycle-{cycle}.json", qa)
    save(ROOT / "final-package-repaired.json", repaired_package)

    print(json.dumps({
        "status": repaired_package["status"],
        "repair_cycle": cycle,
        "strategy_ids": sorted(affected_strategy_ids),
        "page_ids": sorted(affected_pages),
        "qa_issue_count": len(qa.get("issues", [])),
        "qa_issues": qa.get("issues", []),
        "repair_response_id": repair_meta["response_id"],
        "qa_response_id": qa_meta["response_id"],
    }, ensure_ascii=False, indent=2))

    if repaired_package["status"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    main()

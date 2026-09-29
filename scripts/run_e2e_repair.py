#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from lib.openai_responses import call_openai_responses, get_openai_api_key


ROOT = Path("runs/e2e-demo/RFP-TEST-002")
PACKAGE = ROOT / "final-package.json"


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


def evidence_ids(package):
    return {
        ev["evidence_id"]
        for pack in package.get("evidence_packs", [])
        for ev in pack.get("evidence", [])
        if ev.get("evidence_id")
    }


def validate_slide(slide, valid_evidence):
    invalid = set(slide.get("evidence_ids", [])) - valid_evidence
    for block in slide.get("body_blocks", []):
        invalid |= set(block.get("evidence_ids", [])) - valid_evidence
    return sorted(invalid)


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
    issues = package.get("qa", {}).get("issues", [])
    if not issues:
        print("No QA issues; repair not required.")
        return

    affected = {issue.get("page_id") for issue in issues if issue.get("page_id")}
    pages = {
        page["page_id"]: page
        for page in package["pagination"].get("pages", [])
        if page.get("page_id") in affected
    }
    slides = {
        slide["page_id"]: slide
        for slide in package["slides"].get("slides", [])
        if slide.get("page_id") in affected
    }
    visuals = {
        visual["page_id"]: visual
        for visual in package["visuals"].get("visuals", [])
        if visual.get("page_id") in affected
    }

    api_key = get_openai_api_key()
    model = package.get("model", "gpt-5.6-luna")
    valid_evidence = evidence_ids(package)

    repair_prompt = prompt_text("prompts/production/targeted_repair.md") + """

For this demo, repair only the affected page IDs supplied in the input.
Do not rewrite unaffected pages.

Return JSON only:
{
  "repairs": [
    {
      "page_id": "PAGE-001",
      "repaired_slide": { ...complete Slide Draft object... },
      "repaired_visual": { ...complete Visual Prompt object... },
      "repair_summary": [
        {
          "error_type": "string",
          "change": "string",
          "resolved": true
        }
      ]
    }
  ],
  "escalation_required": false,
  "escalation_reason": null
}

Rules:
- Keep the same page_id.
- Preserve evidence IDs only when the evidence directly supports the wording.
- If a detail is not directly supported, remove it or classify it as AI_RECOMMENDATION/client confirmation.
- The repaired visual must not present an unverified detail as an established process.
"""
    repair, repair_meta = call(
        api_key,
        model,
        repair_prompt,
        {
            "qa_issues": issues,
            "affected_pages": pages,
            "current_slides": slides,
            "current_visuals": visuals,
            "evidence_packs": package["evidence_packs"],
            "rfp_analysis": package["rfp_analysis"],
            "proposal_strategy": package["proposal_strategy"],
        },
        5000,
    )

    merged_slides = json.loads(json.dumps(package["slides"], ensure_ascii=False))
    merged_visuals = json.loads(json.dumps(package["visuals"], ensure_ascii=False))
    slide_index = {s["page_id"]: i for i, s in enumerate(merged_slides["slides"])}
    visual_index = {v["page_id"]: i for i, v in enumerate(merged_visuals["visuals"])}

    repair_validation = []
    for item in repair.get("repairs", []):
        page_id = item.get("page_id")
        if page_id not in affected:
            raise SystemExit(f"Repair attempted unaffected page: {page_id}")
        repaired_slide = item.get("repaired_slide")
        repaired_visual = item.get("repaired_visual")
        if not isinstance(repaired_slide, dict) or repaired_slide.get("page_id") != page_id:
            raise SystemExit(f"Invalid repaired slide for {page_id}")
        if not isinstance(repaired_visual, dict) or repaired_visual.get("page_id") != page_id:
            raise SystemExit(f"Invalid repaired visual for {page_id}")
        invalid = validate_slide(repaired_slide, valid_evidence)
        if invalid:
            raise SystemExit(f"Repair introduced invalid evidence IDs: {invalid}")
        merged_slides["slides"][slide_index[page_id]] = repaired_slide
        merged_visuals["visuals"][visual_index[page_id]] = repaired_visual
        repair_validation.append({
            "page_id": page_id,
            "invalid_evidence_ids": invalid,
            "status": "PASS",
        })

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
            "proposal_strategy": package["proposal_strategy"],
            "pagination": package["pagination"],
            "slides": merged_slides,
            "visuals": merged_visuals,
            "previous_qa_issues": issues,
            "repair_validation": repair_validation,
        },
        5000,
    )

    repaired_package = json.loads(json.dumps(package, ensure_ascii=False))
    repaired_package["slides"] = merged_slides
    repaired_package["visuals"] = merged_visuals
    repaired_package["qa"] = qa
    repaired_package["status"] = qa.get("status", "UNKNOWN")
    repaired_package["repair"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repair_output": repair,
        "validation": repair_validation,
        "stage_metadata": {
            "repair": repair_meta,
            "qa_recheck": qa_meta,
        },
    }

    save(ROOT / "repair.json", repair)
    save(ROOT / "slides-repaired.json", merged_slides)
    save(ROOT / "visuals-repaired.json", merged_visuals)
    save(ROOT / "qa-recheck.json", qa)
    save(ROOT / "final-package-repaired.json", repaired_package)

    print(json.dumps({
        "status": repaired_package["status"],
        "repaired_pages": sorted(affected),
        "qa_issue_count": len(qa.get("issues", [])),
        "qa_issues": qa.get("issues", []),
        "repair_response_id": repair_meta["response_id"],
        "qa_response_id": qa_meta["response_id"],
    }, ensure_ascii=False, indent=2))

    if repaired_package["status"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    main()

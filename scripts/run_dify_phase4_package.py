#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from lib.openai_responses import ProviderError, call_openai_responses, get_openai_api_key
from lib.pagination_eval import validate_pagination
from lib.repair_router import route_repairs
from lib.slide_eval import validate_slides
from lib.visual_eval import validate_visuals


DEFAULT_CONFIG = "configs/dify-phase4-package-v1.json"


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_json(raw: str):
    text = raw.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def prompt_text(path: str):
    content = Path(path).read_text(encoding="utf-8")
    if "## Prompt" in content:
        return content.split("## Prompt", 1)[1].strip()
    return content.strip()


def call_stage(api_key: str, config: dict, stage: str, instructions: str, payload: dict):
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


def slide_contract():
    return r'''
Return JSON only:
{
  "slides": [
    {
      "page_id": "PAGE-001",
      "headline": "string",
      "subheadline": "string",
      "body_blocks": [
        {
          "label": "string",
          "text": "string",
          "claim_type": "RFP_FACT | REFERENCE_FACT | REFERENCE_PATTERN | AI_RECOMMENDATION",
          "evidence_ids": ["EV-R-201-01"],
          "client_confirmation_required": false
        }
      ],
      "evidence_ids": ["EV-R-201-01"],
      "visual_type": "none | icon_diagram | process_diagram | illustration | photo | data_chart | reference_image",
      "speaker_note": "string",
      "fact_risk": "low | medium | high"
    }
  ]
}

Strict batch rules:
- Return exactly one slide for every supplied page_id, with no extra page IDs.
- Keep each slide scoped to its page requirement_ids, strategy_ids, and allowed evidence IDs.
- slide.evidence_ids must equal the union of evidence_ids used by its body_blocks.
- REFERENCE_FACT and REFERENCE_PATTERN blocks require direct supporting evidence_ids.
- RFP_FACT and AI_RECOMMENDATION blocks must have evidence_ids=[].
- Do not broaden evidence wording. Every independently meaningful clause in a reference-backed block must be directly entailed by supported_point, reusable_patterns, or company_facts.\n- Evidence scope outranks upstream strategy/page wording: if a strategy or page says more than the cited evidence directly supports, narrow the slide to the evidence-supported wording instead of copying the broader upstream phrase.\n- Do not turn generic evidence such as "one action goal" into specific examples unless those examples are explicitly supported by the same evidence.
- If a useful idea is not directly supported by reference evidence, split it into AI_RECOMMENDATION with evidence_ids=[].
- Do not introduce quantitative values unless they are present in the supplied RFP facts or the cited evidence.\n- If the validated slide contains no actual quantitative values, never choose visual_type=data_chart; use process_diagram, icon_diagram, illustration, photo, or none instead.\n- AI_RECOMMENDATION numeric targets require client_confirmation_required=true.
'''


def visual_contract():
    return r'''
Return JSON only:
{
  "visuals": [
    {
      "page_id": "PAGE-001",
      "visual_type": "process_diagram",
      "do_not_generate": false,
      "purpose": "string",
      "image_prompt": "string | null",
      "diagram_spec": {
        "nodes": [],
        "edges": []
      },
      "data_source": ["EV-R-201-01"],
      "prohibited_elements": [],
      "fact_risk": "low | medium | high"
    }
  ]
}

Strict batch rules:
- Return exactly one visual spec for every validated slide page_id.
- visual_type must exactly match the slide visual_type.
- data_source may contain only evidence IDs already used by that slide.
- Do not add stages, actors, metrics, numbers, locations, clients, or operational facts that are absent from the validated slide.
- Do not invent conversion rates, percentages, chart axes, or quantitative results.\n- Numeric values already present in the supplied Pagination page or validated Slide may be reused exactly.\n- data_chart is allowed only when the validated slide contains actual quantitative data.
- reference_image is unavailable in this Phase 4 run.
- process_diagram requires explicit nodes and edges.
- visual_type=none requires do_not_generate=true and image_prompt=null.
'''


def qa_contract():
    return r'''
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

Review the final package semantically, not just structurally.
Treat each independently meaningful clause as a separate claim for evidence entailment.
A cited evidence item must directly support the wording; keyword overlap is not enough.
Do not report an issue that has already been prevented by the deterministic validation gates.
If there is no real issue, return PASS with issues=[].
'''


def repair_contract():
    return r'''
Return JSON only:
{
  "strategy_repairs": [
    {
      "strategy_id": "ST-01",
      "repaired_pillar": { "...": "complete strategy pillar" }
    }
  ],
  "page_repairs": [
    {
      "page_id": "PAGE-001",
      "repaired_page": { "...": "complete pagination page or null" },
      "repaired_slide": { "...": "complete slide or null" },
      "repaired_visual": { "...": "complete visual or null" }
    }
  ],
  "repair_summary": [
    {
      "error_type": "INVALID_REFERENCE",
      "target_id": "PAGE-001",
      "change": "string",
      "resolved": true
    }
  ],
  "escalation_required": false,
  "escalation_reason": null
}

Repair only supplied target strategy_ids and page_ids.
Do not modify any unaffected strategy pillar or page.
Preserve canonical IDs.
Do not invent evidence IDs.
For REFERENCE_FACT / REFERENCE_PATTERN, every meaningful clause must be directly supported by cited evidence.\nEvidence scope is authoritative: repair broader strategy/page/slide wording downward to supported_point/reusable_patterns rather than treating upstream wording as proof.
If wording exceeds evidence, narrow it or move the unsupported idea into AI_RECOMMENDATION with no evidence IDs.
Return complete replacement objects for every object you choose to repair.
'''


def evidence_by_requirement(evidence_packs: list[dict]):
    return {
        pack.get("requirement_id"): pack
        for pack in evidence_packs
        if pack.get("requirement_id")
    }


def strategy_by_id(strategy: dict):
    return {
        pillar.get("strategy_id"): pillar
        for pillar in strategy.get("strategy_pillars", [])
        if pillar.get("strategy_id")
    }


def build_slide_input(phase2: dict, phase3: dict):
    requirements = {
        item.get("id"): item
        for item in phase2["rfp_analysis"].get("requirements", [])
        if item.get("id")
    }
    strategies = strategy_by_id(phase2["proposal_strategy"])
    evidence = evidence_by_requirement(phase2["evidence_packs"])

    pages = []
    for page in phase3["pagination"].get("pages", []):
        requirement_ids = page.get("rfp_requirement_ids", [])
        strategy_ids = page.get("strategy_ids", [])
        pages.append({
            "page": page,
            "requirements": [
                requirements[rid]
                for rid in requirement_ids
                if rid in requirements
            ],
            "strategy_pillars": [
                strategies[sid]
                for sid in strategy_ids
                if sid in strategies
            ],
            "evidence_packs": [
                evidence[rid]
                for rid in requirement_ids
                if rid in evidence
            ],
        })
    return pages


def build_visual_input(phase2: dict, phase3: dict, slides: dict):
    page_by_id = {
        page["page_id"]: page
        for page in phase3["pagination"].get("pages", [])
    }
    evidence = evidence_by_requirement(phase2["evidence_packs"])
    rows = []
    for slide in slides.get("slides", []):
        page = page_by_id[slide["page_id"]]
        rows.append({
            "page": page,
            "slide": slide,
            "evidence_packs": [
                evidence[rid]
                for rid in page.get("rfp_requirement_ids", [])
                if rid in evidence
            ],
        })
    return rows


def build_provenance_chain(strategy: dict, pagination: dict, slides: dict, visuals: dict, evidence_packs: list[dict]):
    evidence_index = {}
    for pack in evidence_packs:
        for evidence in pack.get("evidence", []):
            evidence_id = evidence.get("evidence_id")
            if evidence_id:
                evidence_index[evidence_id] = {
                    "asset_id": evidence.get("asset_id"),
                    "requirement_id": pack.get("requirement_id"),
                }

    strategy_index = strategy_by_id(strategy)
    slide_index = {slide["page_id"]: slide for slide in slides.get("slides", [])}
    visual_index = {visual["page_id"]: visual for visual in visuals.get("visuals", [])}
    chains = []
    broken = []

    for page in pagination.get("pages", []):
        page_id = page.get("page_id")
        slide = slide_index.get(page_id)
        visual = visual_index.get(page_id)
        for requirement_id in page.get("rfp_requirement_ids", []):
            for strategy_id in page.get("strategy_ids", []):
                pillar = strategy_index.get(strategy_id)
                relevant_evidence_ids = [
                    evidence_id
                    for evidence_id in page.get("evidence_ids", [])
                    if evidence_index.get(evidence_id, {}).get("requirement_id") == requirement_id
                ]
                if not relevant_evidence_ids:
                    relevant_evidence_ids = [None]
                for evidence_id in relevant_evidence_ids:
                    evidence = evidence_index.get(evidence_id) if evidence_id else None
                    row = {
                        "requirement_id": requirement_id,
                        "asset_id": evidence.get("asset_id") if evidence else None,
                        "evidence_id": evidence_id,
                        "strategy_id": strategy_id,
                        "page_id": page_id,
                        "slide_present": slide is not None,
                        "visual_present": visual is not None,
                        "valid": bool(
                            pillar
                            and slide
                            and visual
                            and (evidence_id is None or evidence)
                        ),
                    }
                    chains.append(row)
                    if not row["valid"]:
                        broken.append(row)

    return {
        "chains": chains,
        "broken_chains": broken,
        "pass": not broken,
    }


def merge_repairs(package: dict, repair: dict, route: dict):
    strategy = deepcopy(package["proposal_strategy"])
    pagination = deepcopy(package["pagination"])
    slides = deepcopy(package["slides"])
    visuals = deepcopy(package["visuals"])

    strategy_index = {
        item["strategy_id"]: i
        for i, item in enumerate(strategy.get("strategy_pillars", []))
        if item.get("strategy_id")
    }
    page_index = {
        item["page_id"]: i
        for i, item in enumerate(pagination.get("pages", []))
        if item.get("page_id")
    }
    slide_index = {
        item["page_id"]: i
        for i, item in enumerate(slides.get("slides", []))
        if item.get("page_id")
    }
    visual_index = {
        item["page_id"]: i
        for i, item in enumerate(visuals.get("visuals", []))
        if item.get("page_id")
    }

    allowed_strategy_ids = set(route["strategy_ids"])
    allowed_page_ids = set(route["page_ids"])

    for item in repair.get("strategy_repairs", []):
        strategy_id = item.get("strategy_id")
        repaired = item.get("repaired_pillar")
        if strategy_id not in allowed_strategy_ids:
            raise ValueError(f"Repair attempted unaffected strategy: {strategy_id}")
        if strategy_id not in strategy_index:
            raise ValueError(f"Unknown repaired strategy: {strategy_id}")
        if not isinstance(repaired, dict):
            raise ValueError(f"Invalid strategy repair for {strategy_id}")
        nested_strategy_id = repaired.get("strategy_id")
        if nested_strategy_id not in (None, "", strategy_id):
            raise ValueError(
                f"Conflicting strategy_id in repair for {strategy_id}: "
                f"{nested_strategy_id}"
            )
        repaired["strategy_id"] = strategy_id
        strategy["strategy_pillars"][strategy_index[strategy_id]] = repaired

    for item in repair.get("page_repairs", []):
        page_id = item.get("page_id")
        if page_id not in allowed_page_ids:
            raise ValueError(f"Repair attempted unaffected page: {page_id}")

        repaired_page = item.get("repaired_page")
        repaired_slide = item.get("repaired_slide")
        repaired_visual = item.get("repaired_visual")

        if repaired_page is not None:
            if page_id not in page_index or not isinstance(repaired_page, dict):
                raise ValueError(f"Invalid pagination repair for {page_id}")
            nested_page_id = repaired_page.get("page_id")
            if nested_page_id not in (None, "", page_id):
                raise ValueError(
                    f"Conflicting repaired_page.page_id for {page_id}: "
                    f"{nested_page_id}"
                )
            repaired_page["page_id"] = page_id
            pagination["pages"][page_index[page_id]] = repaired_page

        if repaired_slide is not None:
            if page_id not in slide_index or not isinstance(repaired_slide, dict):
                raise ValueError(f"Invalid slide repair for {page_id}")
            nested_page_id = repaired_slide.get("page_id")
            if nested_page_id not in (None, "", page_id):
                raise ValueError(
                    f"Conflicting repaired_slide.page_id for {page_id}: "
                    f"{nested_page_id}"
                )
            repaired_slide["page_id"] = page_id
            slides["slides"][slide_index[page_id]] = repaired_slide

        if repaired_visual is not None:
            if page_id not in visual_index or not isinstance(repaired_visual, dict):
                raise ValueError(f"Invalid visual repair for {page_id}")
            nested_page_id = repaired_visual.get("page_id")
            if nested_page_id not in (None, "", page_id):
                raise ValueError(
                    f"Conflicting repaired_visual.page_id for {page_id}: "
                    f"{nested_page_id}"
                )
            repaired_visual["page_id"] = page_id
            visuals["visuals"][visual_index[page_id]] = repaired_visual

    return strategy, pagination, slides, visuals


def run_gates(phase2: dict, strategy: dict, pagination: dict, slides: dict, visuals: dict, page_limit: int):
    coverage = validate_pagination(
        pagination,
        phase2["rfp_analysis"],
        strategy,
        phase2["evidence_packs"],
        page_limit=page_limit,
    )
    slide_gate = validate_slides(
        slides,
        pagination,
        phase2["rfp_analysis"],
        phase2["evidence_packs"],
    )
    visual_gate = validate_visuals(
        visuals,
        slides,
        pagination,
    )
    return {
        "coverage": coverage,
        "slide": slide_gate,
        "visual": visual_gate,
        "pass": (
            coverage["status"] == "PASS"
            and slide_gate["status"] == "PASS"
            and visual_gate["status"] == "PASS"
        ),
    }


def render_markdown(result: dict):
    gates = result["validation"]["gates"]
    provenance = result["validation"]["provenance"]
    qa = result["qa"]
    lines = [
        "# Dify Phase 4 — Final Package",
        "",
        f'- RFP: {result["rfp_id"]}',
        f'- status: **{result["status"]}**',
        f'- model: {result["model"]}',
        f'- pages: **{len(result["pagination"].get("pages", []))}**',
        f'- slides: **{len(result["slides"].get("slides", []))}**',
        f'- visuals: **{len(result["visuals"].get("visuals", []))}**',
        f'- repair cycles: **{len(result.get("repair_history", []))}**',
        "",
        "## Deterministic gates",
        "",
        f'- coverage: **{gates["coverage"]["status"]}**',
        f'- slide provenance: **{gates["slide"]["status"]}**',
        f'- visual provenance: **{gates["visual"]["status"]}**',
        f'- broken provenance chains: **{len(provenance["broken_chains"])}**',
        "",
        "## Semantic QA",
        "",
        f'- status: **{qa.get("status")}**',
        f'- issues: **{len(qa.get("issues", []))}**',
        f'- summary: {qa.get("summary", "")}',
        "",
        "## Requirement → Asset → Evidence → Strategy → Page",
        "",
    ]
    for row in provenance["chains"]:
        lines.append(
            "- {requirement_id} → {asset_id} → {evidence_id} → "
            "{strategy_id} → {page_id}".format(**row)
        )

    if result.get("repair_history"):
        lines.extend(["", "## Repair history", ""])
        for repair in result["repair_history"]:
            lines.append(
                f'- cycle {repair["cycle"]}: scope={repair["route"].get("scope")} '
                f'pages={repair["route"].get("page_ids")} '
                f'strategies={repair["route"].get("strategy_ids")}'
            )

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    phase2 = load_json(config["sources"]["phase2"])
    phase3 = load_json(config["sources"]["phase3"])

    if phase2.get("status") != "PASS":
        raise SystemExit("Phase 2 source must be PASS.")
    if phase3.get("status") != "PASS":
        raise SystemExit("Phase 3 source must be PASS.")

    plan = {
        "phase": config["phase"],
        "rfp_id": config["rfp_id"],
        "model": config["model"],
        "normal_path_openai_calls": 3,
        "repair_calls_per_cycle": 2,
        "max_repair_cycles": config["max_repair_cycles"],
        "max_total_calls": 3 + (2 * config["max_repair_cycles"]),
        "source_phase2": config["sources"]["phase2"],
        "source_phase3": config["sources"]["phase3"],
        "output_root": config["output_root"],
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    api_key = get_openai_api_key()
    stage_metadata = {}

    slides, stage_metadata["slide_draft"] = call_stage(
        api_key,
        config,
        "slide_draft",
        prompt_text(config["prompts"]["slide_draft"]) + "\n\n" + slide_contract(),
        {
            "rfp_id": config["rfp_id"],
            "pages": build_slide_input(phase2, phase3),
        },
    )

    slide_gate = validate_slides(
        slides,
        phase3["pagination"],
        phase2["rfp_analysis"],
        phase2["evidence_packs"],
    )
    if slide_gate["status"] != "PASS":
        result = {
            "status": "FAIL",
            "stage": "slide_gate",
            "slide_gate": slide_gate,
            "slides": slides,
        }
        save_json(Path(config["output_root"]) / "slide-gate-failure.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(3)

    visuals, stage_metadata["visual_prompt"] = call_stage(
        api_key,
        config,
        "visual_prompt",
        prompt_text(config["prompts"]["visual_prompt"]) + "\n\n" + visual_contract(),
        {
            "rfp_id": config["rfp_id"],
            "slides": build_visual_input(phase2, phase3, slides),
        },
    )

    initial_gates = run_gates(
        phase2,
        phase2["proposal_strategy"],
        phase3["pagination"],
        slides,
        visuals,
        int(phase3["page_limit"]),
    )
    if not initial_gates["pass"]:
        result = {
            "status": "FAIL",
            "stage": "visual_gate",
            "gates": initial_gates,
            "slides": slides,
            "visuals": visuals,
        }
        save_json(Path(config["output_root"]) / "visual-gate-failure.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(3)

    package = {
        "version": config["version"],
        "phase": config["phase"],
        "status": "PENDING_QA",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rfp_id": config["rfp_id"],
        "model": config["model"],
        "rfp_analysis": phase2["rfp_analysis"],
        "evidence_packs": phase2["evidence_packs"],
        "proposal_strategy": deepcopy(phase2["proposal_strategy"]),
        "pagination": deepcopy(phase3["pagination"]),
        "slides": slides,
        "visuals": visuals,
        "repair_history": [],
    }

    qa, stage_metadata["proposal_qa"] = call_stage(
        api_key,
        config,
        "proposal_qa",
        prompt_text(config["prompts"]["proposal_qa"]) + "\n\n" + qa_contract(),
        {
            "rfp_id": config["rfp_id"],
            "rfp_analysis": package["rfp_analysis"],
            "evidence_packs": package["evidence_packs"],
            "proposal_strategy": package["proposal_strategy"],
            "pagination": package["pagination"],
            "slides": package["slides"],
            "visuals": package["visuals"],
            "deterministic_gate_results": initial_gates,
        },
    )
    package["qa"] = qa

    root = Path(config["output_root"])
    root.mkdir(parents=True, exist_ok=True)
    save_json(root / "slides-initial.json", slides)
    save_json(root / "visuals-initial.json", visuals)
    save_json(root / "qa-initial.json", qa)

    repair_history = []
    for cycle in range(1, int(config["max_repair_cycles"]) + 1):
        if qa.get("status") == "PASS" and not qa.get("issues"):
            break

        route = route_repairs(qa.get("issues", []), package["pagination"])
        if route["escalation_required"]:
            package["status"] = "ESCALATION_REQUIRED"
            package["escalation"] = route
            break

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
        strategy_index = strategy_by_id(package["proposal_strategy"])
        affected_requirements = {
            requirement_id
            for page_id in route["page_ids"]
            for requirement_id in page_by_id.get(page_id, {}).get("rfp_requirement_ids", [])
        }
        relevant_evidence = [
            pack
            for pack in package["evidence_packs"]
            if pack.get("requirement_id") in affected_requirements
        ]

        repair, repair_meta = call_stage(
            api_key,
            config,
            "targeted_repair",
            prompt_text(config["prompts"]["targeted_repair"]) + "\n\n" + repair_contract(),
            {
                "repair_cycle": cycle,
                "route": route,
                "qa_issues": qa.get("issues", []),
                "affected_strategy_pillars": {
                    strategy_id: strategy_index[strategy_id]
                    for strategy_id in route["strategy_ids"]
                    if strategy_id in strategy_index
                },
                "affected_pages": {
                    page_id: page_by_id[page_id]
                    for page_id in route["page_ids"]
                    if page_id in page_by_id
                },
                "affected_slides": {
                    page_id: slide_by_id[page_id]
                    for page_id in route["page_ids"]
                    if page_id in slide_by_id
                },
                "affected_visuals": {
                    page_id: visual_by_id[page_id]
                    for page_id in route["page_ids"]
                    if page_id in visual_by_id
                },
                "relevant_evidence_packs": relevant_evidence,
                "rfp_analysis": package["rfp_analysis"],
            },
        )

        if repair.get("escalation_required"):
            package["status"] = "ESCALATION_REQUIRED"
            package["escalation"] = {
                "route": route,
                "repair_reason": repair.get("escalation_reason"),
            }
            break

        try:
            strategy, pagination, repaired_slides, repaired_visuals = merge_repairs(
                package,
                repair,
                route,
            )
        except ValueError as exc:
            package["status"] = "ESCALATION_REQUIRED"
            package["escalation"] = {
                "route": route,
                "repair_reason": str(exc),
            }
            break

        gates = run_gates(
            phase2,
            strategy,
            pagination,
            repaired_slides,
            repaired_visuals,
            int(phase3["page_limit"]),
        )
        if not gates["pass"]:
            package["status"] = "ESCALATION_REQUIRED"
            package["escalation"] = {
                "route": route,
                "repair_reason": "Repair failed deterministic gates.",
                "gates": gates,
            }
            break

        package["proposal_strategy"] = strategy
        package["pagination"] = pagination
        package["slides"] = repaired_slides
        package["visuals"] = repaired_visuals

        qa, qa_meta = call_stage(
            api_key,
            config,
            "proposal_qa",
            prompt_text(config["prompts"]["proposal_qa"]) + "\n\n" + qa_contract(),
            {
                "rfp_id": config["rfp_id"],
                "rfp_analysis": package["rfp_analysis"],
                "evidence_packs": package["evidence_packs"],
                "proposal_strategy": package["proposal_strategy"],
                "pagination": package["pagination"],
                "slides": package["slides"],
                "visuals": package["visuals"],
                "previous_qa_issues": package["qa"].get("issues", []),
                "repair_output": repair,
                "deterministic_gate_results": gates,
            },
        )
        package["qa"] = qa

        history_row = {
            "cycle": cycle,
            "route": route,
            "repair_output": repair,
            "gates": gates,
            "stage_metadata": {
                "repair": repair_meta,
                "qa_recheck": qa_meta,
            },
        }
        repair_history.append(history_row)
        save_json(root / f"repair-cycle-{cycle}.json", repair)
        save_json(root / f"qa-recheck-cycle-{cycle}.json", qa)
        save_json(root / f"package-cycle-{cycle}.json", package)

    package["repair_history"] = repair_history

    final_gates = run_gates(
        phase2,
        package["proposal_strategy"],
        package["pagination"],
        package["slides"],
        package["visuals"],
        int(phase3["page_limit"]),
    )
    provenance = build_provenance_chain(
        package["proposal_strategy"],
        package["pagination"],
        package["slides"],
        package["visuals"],
        package["evidence_packs"],
    )

    if package.get("status") != "ESCALATION_REQUIRED":
        if (
            final_gates["pass"]
            and provenance["pass"]
            and package["qa"].get("status") == "PASS"
            and not package["qa"].get("issues")
        ):
            package["status"] = "PASS"
        else:
            package["status"] = "ESCALATION_REQUIRED"

    package["validation"] = {
        "gates": final_gates,
        "provenance": provenance,
    }
    package["stage_metadata"] = stage_metadata

    save_json(root / "final-package.json", package)
    save_json(Path(config["report_json"]), package)
    Path(config["report_md"]).parent.mkdir(parents=True, exist_ok=True)
    Path(config["report_md"]).write_text(render_markdown(package), encoding="utf-8")

    print(json.dumps({
        "status": package["status"],
        "rfp_id": package["rfp_id"],
        "pages": len(package["pagination"].get("pages", [])),
        "slides": len(package["slides"].get("slides", [])),
        "visuals": len(package["visuals"].get("visuals", [])),
        "repair_cycles": len(repair_history),
        "qa_status": package["qa"].get("status"),
        "qa_issue_count": len(package["qa"].get("issues", [])),
        "coverage_gate": final_gates["coverage"]["status"],
        "slide_gate": final_gates["slide"]["status"],
        "visual_gate": final_gates["visual"]["status"],
        "broken_provenance_chains": len(provenance["broken_chains"]),
        "report": config["report_json"],
    }, ensure_ascii=False, indent=2))

    if package["status"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    try:
        main()
    except (ProviderError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

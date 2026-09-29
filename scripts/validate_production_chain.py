#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REQUIRED_PROMPTS = [
    "prompts/production/rfp_analyzer.md",
    "prompts/production/retrieval_planner.md",
    "prompts/production/evidence_builder.md",
    "prompts/production/proposal_strategist.md",
    "prompts/production/pagination.md",
    "prompts/production/coverage_validator.md",
    "prompts/production/slide_draft.md",
    "prompts/production/visual_prompt.md",
    "prompts/production/proposal_qa.md",
    "prompts/production/targeted_repair.md",
]

REQUIRED_STAGE_IDS = [
    "rfp_analyzer",
    "retrieval_planner",
    "knowledge_retrieval",
    "evidence_builder",
    "proposal_strategist",
    "human_strategy_review",
    "pagination_planner",
    "coverage_validator",
    "slide_draft_loop",
    "visual_prompt_loop",
    "proposal_qa",
    "targeted_repair",
    "final_output",
]


def main():
    missing = [path for path in REQUIRED_PROMPTS if not Path(path).exists()]
    if missing:
        raise SystemExit(f"Missing production prompt files: {missing}")

    spec_path = Path("dify/workflow-spec.yaml")
    if not spec_path.exists():
        raise SystemExit("Missing dify/workflow-spec.yaml")
    spec = spec_path.read_text(encoding="utf-8")
    missing_stages = [stage for stage in REQUIRED_STAGE_IDS if f"id: {stage}" not in spec]
    if missing_stages:
        raise SystemExit(f"Missing workflow stages: {missing_stages}")

    prompt_refs = [line.strip().split("prompt:", 1)[1].strip() for line in spec.splitlines() if "prompt:" in line]
    bad_refs = [ref for ref in prompt_refs if not Path(ref).exists()]
    if bad_refs:
        raise SystemExit(f"Workflow references missing prompt files: {bad_refs}")

    print(f"production_prompts={len(REQUIRED_PROMPTS)} workflow_stages={len(REQUIRED_STAGE_IDS)} prompt_refs={len(prompt_refs)}")


if __name__ == "__main__":
    main()

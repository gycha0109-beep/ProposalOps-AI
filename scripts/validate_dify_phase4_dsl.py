#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_DSL = "dify/proposalops-phase4-package.yml"
EXPECTED_VERSION = "0.7.0"
PRODUCTION_DATASET_ID = "21dcb1f3-270f-4991-bcf8-b2782e6cf814"
BENCHMARK_DATASET_ID = "e72cbe16-1eef-4858-9e35-61d5e00326bf"


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsl", default=DEFAULT_DSL)
    args = parser.parse_args()

    path = Path(args.dsl)
    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("kind") != "app":
        fail("DSL kind must be app.")
    if data.get("version") != EXPECTED_VERSION:
        fail(f"DSL version must be {EXPECTED_VERSION}.")
    if (data.get("app") or {}).get("mode") != "workflow":
        fail("App mode must be workflow.")

    graph = ((data.get("workflow") or {}).get("graph") or {})
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if len(nodes) != 42 or len(edges) != 43:
        fail(f"Expected 42 nodes / 43 edges, got {len(nodes)} / {len(edges)}.")

    by_id = {node.get("id"): node for node in nodes}
    if len(by_id) != len(nodes) or None in by_id:
        fail("Node IDs must be unique and non-null.")

    expected_ids = {
        "start",
        "rfp_analyzer",
        "retrieval_planner",
        "parse_plans",
        "query_iteration",
        "query_iteration_start",
        "parse_item",
        "rate_limit_delay",
        "knowledge_retrieval",
        "pack_retrieval",
        "normalize_retrieval",
        "evidence_builder",
        "proposal_strategist",
        "pagination_planner",
        "coverage_validator",
        "slide_draft",
        "slide_gate",
        "slide_gate_branch",
        "visual_prompt",
        "visual_gate",
        "visual_gate_branch",
        "proposal_qa",
        "qa_parse",
        "qa_branch",
        "repair_context",
        "targeted_repair",
        "repair_merge_gate",
        "repair_gate_branch",
        "qa_recheck",
        "qa_recheck_parse",
        "qa_recheck_branch",
        "visual_repair",
        "visual_repair_gate",
        "visual_repair_branch",
        "proposal_qa_after_visual_repair",
        "qa_parse_after_visual_repair",
        "qa_branch_after_visual_repair",
        "visual_repaired_final_end",
        "final_end",
        "gate_failure_end",
        "repaired_end",
        "escalation_end",
    }
    if set(by_id) != expected_ids:
        fail(
            "Unexpected node IDs. "
            f"missing={sorted(expected_ids - set(by_id))} "
            f"extra={sorted(set(by_id) - expected_ids)}"
        )

    node_types = Counter((node.get("data") or {}).get("type") for node in nodes)
    required_counts = {
        "start": 1,
        "llm": 12,
        "code": 14,
        "iteration": 1,
        "iteration-start": 1,
        "knowledge-retrieval": 1,
        "if-else": 7,
        "end": 5,
    }
    if dict(node_types) != required_counts:
        fail(f"Unexpected node type counts: {dict(node_types)}")

    for edge in edges:
        if edge.get("source") not in by_id:
            fail(f"Edge source does not exist: {edge.get('source')}")
        if edge.get("target") not in by_id:
            fail(f"Edge target does not exist: {edge.get('target')}")

    required_edges = {
        ("coverage_validator", "slide_draft", "source"),
        ("slide_draft", "slide_gate", "source"),
        ("slide_gate", "slide_gate_branch", "source"),
        ("slide_gate_branch", "visual_prompt", "true"),
        ("slide_gate_branch", "gate_failure_end", "false"),
        ("visual_prompt", "visual_gate", "source"),
        ("visual_gate", "visual_gate_branch", "source"),
        ("visual_gate_branch", "proposal_qa", "true"),
        ("visual_gate_branch", "gate_failure_end", "false"),
        ("proposal_qa", "qa_parse", "source"),
        ("qa_parse", "qa_branch", "source"),
        ("qa_branch", "final_end", "true"),
        ("qa_branch", "repair_context", "false"),
        ("repair_context", "targeted_repair", "source"),
        ("targeted_repair", "repair_merge_gate", "source"),
        ("repair_merge_gate", "repair_gate_branch", "source"),
        ("repair_gate_branch", "qa_recheck", "true"),
        ("repair_gate_branch", "escalation_end", "false"),
        ("qa_recheck", "qa_recheck_parse", "source"),
        ("qa_recheck_parse", "qa_recheck_branch", "source"),
        ("qa_recheck_branch", "repaired_end", "true"),
        ("qa_recheck_branch", "escalation_end", "false"),
        ("visual_gate_branch", "visual_repair", "false"),
        ("visual_repair", "visual_repair_gate", "source"),
        ("visual_repair_gate", "visual_repair_branch", "source"),
        ("visual_repair_branch", "proposal_qa_after_visual_repair", "true"),
        ("visual_repair_branch", "gate_failure_end", "false"),
        ("proposal_qa_after_visual_repair", "qa_parse_after_visual_repair", "source"),
        ("qa_parse_after_visual_repair", "qa_branch_after_visual_repair", "source"),
        ("qa_branch_after_visual_repair", "visual_repaired_final_end", "true"),
        ("qa_branch_after_visual_repair", "escalation_end", "false"),
    }
    actual_edges = {
        (edge.get("source"), edge.get("target"), edge.get("sourceHandle"))
        for edge in edges
    }
    missing_edges = sorted(required_edges - actual_edges)
    if missing_edges:
        fail(f"Phase 4 wiring is incomplete: {missing_edges}")

    iteration = by_id["query_iteration"]["data"]
    if iteration.get("is_parallel") is not False:
        fail("Query iteration must remain serial for Sandbox rate-limit safety.")
    if iteration.get("iterator_input_type") != "array[string]":
        fail("Query iteration input must remain array[string].")
    if "time.sleep(7)" not in by_id["rate_limit_delay"]["data"].get("code", ""):
        fail("Sandbox rate-limit delay must remain 7 seconds.")

    knowledge = by_id["knowledge_retrieval"]["data"]
    dataset_ids = knowledge.get("dataset_ids") or []
    if dataset_ids != [PRODUCTION_DATASET_ID]:
        fail(f"Knowledge node must use production dataset only: {dataset_ids}")
    if BENCHMARK_DATASET_ID in dataset_ids:
        fail("Benchmark dataset must never be wired into production workflow.")

    llm_ids = {
        "rfp_analyzer",
        "retrieval_planner",
        "evidence_builder",
        "proposal_strategist",
        "pagination_planner",
        "slide_draft",
        "visual_prompt",
        "proposal_qa",
        "targeted_repair",
        "qa_recheck",
        "visual_repair",
        "proposal_qa_after_visual_repair",
    }
    for node_id in llm_ids:
        model = by_id[node_id]["data"].get("model") or {}
        if model.get("provider") != "langgenius/openai/openai":
            fail(f"{node_id} must use the OpenAI provider binding.")
        if model.get("name") != "gpt-5.6-luna":
            fail(f"{node_id} must use gpt-5.6-luna.")
        if model.get("mode") != "chat":
            fail(f"{node_id} must use chat mode.")

    for node_id, selector in {
        "slide_gate": ("slide_draft", "text"),
        "visual_gate": ("visual_prompt", "text"),
        "qa_parse": ("proposal_qa", "text"),
        "repair_context": ("qa_parse", "normalized"),
        "qa_recheck_parse": ("qa_recheck", "text"),
        "visual_repair_gate": ("visual_repair", "text"),
        "qa_parse_after_visual_repair": ("proposal_qa_after_visual_repair", "text"),
    }.items():
        variables = by_id[node_id]["data"].get("variables") or []
        selectors = {
            tuple(item.get("value_selector") or [])
            for item in variables
        }
        if selector not in selectors:
            fail(f"{node_id} is missing selector {selector}.")

    code_markers = {
        "slide_gate": [
            "REFERENCE_WITHOUT_EVIDENCE",
            "OFF_PAGE_EVIDENCE",
            "SLIDE_EVIDENCE_SUMMARY_MISMATCH",
        ],
        "visual_gate": [
            "VISUAL_TYPE_MISMATCH",
            "DATA_CHART_WITHOUT_NUMERIC_INPUT",
            "VISUAL_INVENTED_NUMBER",
        ],
        "repair_context": [
            "strategy_to_visual",
            "pagination_to_visual",
            "slide_visual",
        ],
        "repair_merge_gate": [
            "INVALID_STRATEGY_REPAIR",
            "STRATEGY_ID_CONFLICT",
            "PAGE_ID_CONFLICT",
            "PAGE_SET_MISMATCH",
        ],
    }
    for node_id, markers in code_markers.items():
        code = by_id[node_id]["data"].get("code", "")
        missing = [marker for marker in markers if marker not in code]
        if missing:
            fail(f"{node_id} is missing markers: {missing}")

    numeric_code = by_id["visual_gate"]["data"].get("code", "")
    if r'NUM=re.compile(r"\d+' not in numeric_code:
        fail("Visual numeric regex must match digits, not a literal backslash-d sequence.")

    for branch_id in (
        "slide_gate_branch",
        "visual_gate_branch",
        "qa_branch",
        "repair_gate_branch",
        "qa_recheck_branch",
        "visual_repair_branch",
        "qa_branch_after_visual_repair",
    ):
        branch = by_id[branch_id]["data"]
        targets = {item.get("id") for item in branch.get("_targetBranches") or []}
        if targets != {"true", "false"}:
            fail(f"{branch_id} must expose true/false branches.")
        cases = branch.get("cases") or []
        if len(cases) != 1 or cases[0].get("case_id") != "true":
            fail(f"{branch_id} must have one PASS condition case.")
        conditions = cases[0].get("conditions") or []
        if len(conditions) != 1:
            fail(f"{branch_id} must have one condition.")
        condition = conditions[0]
        if condition.get("comparison_operator") != "is" or condition.get("value") != "PASS":
            fail(f"{branch_id} must branch on status is PASS.")

    qa_prompt = json.dumps(
        by_id["proposal_qa"]["data"].get("prompt_template") or [],
        ensure_ascii=False,
    )
    for marker in ("INVALID_REFERENCE", "CROSS_PROPOSAL_MERGE", "OVERLONG_SLIDE"):
        if marker not in qa_prompt:
            fail(f"Proposal QA prompt is missing taxonomy marker: {marker}")

    slide_prompt = json.dumps(
        by_id["slide_draft"]["data"].get("prompt_template") or [],
        ensure_ascii=False,
    )
    for marker in ("Evidence scope is authoritative", "REFERENCE_PATTERN", "data_chart"):
        if marker not in slide_prompt:
            fail(f"Slide Draft prompt is missing marker: {marker}")

    final_vars = {
        item.get("variable")
        for item in by_id["final_end"]["data"].get("outputs") or []
    }
    expected_final_vars = {
        "rfp_analysis",
        "evidence_packs",
        "proposal_strategy",
        "pagination",
        "slides",
        "visuals",
        "qa",
        "coverage_validation",
        "slide_validation",
        "visual_validation",
    }
    if final_vars != expected_final_vars:
        fail(f"Normal final output mismatch: {sorted(final_vars)}")

    repaired_vars = {
        item.get("variable")
        for item in by_id["repaired_end"]["data"].get("outputs") or []
    }
    visual_repaired_vars = {
        item.get("variable")
        for item in by_id["visual_repaired_final_end"]["data"].get("outputs") or []
    }
    expected_visual_repaired_vars = {
        "visual_repaired_rfp_analysis",
        "visual_repaired_evidence_packs",
        "visual_repaired_proposal_strategy",
        "visual_repaired_pagination",
        "visual_repaired_slides",
        "visual_repaired_visuals",
        "visual_repaired_qa",
        "visual_repaired_coverage_validation",
        "visual_repaired_slide_validation",
        "visual_repaired_visual_validation",
    }
    if visual_repaired_vars != expected_visual_repaired_vars:
        fail(f"Visual-repaired final output mismatch: {sorted(visual_repaired_vars)}")

    expected_repaired_vars = {
        "repaired_rfp_analysis",
        "repaired_evidence_packs",
        "repaired_proposal_strategy",
        "repaired_pagination",
        "repaired_slides",
        "repaired_visuals",
        "repaired_qa",
        "repaired_repair_validation",
    }
    if repaired_vars != expected_repaired_vars:
        fail(f"Repaired final output mismatch: {sorted(repaired_vars)}")

    gate_failure_vars = {
        item.get("variable")
        for item in by_id["gate_failure_end"]["data"].get("outputs") or []
    }
    expected_gate_failure_vars = {
        "gate_failure_coverage_validation",
        "gate_failure_slide_validation",
        "gate_failure_visual_validation",
    }
    if gate_failure_vars != expected_gate_failure_vars:
        fail(f"Gate failure output mismatch: {sorted(gate_failure_vars)}")

    escalation_vars = {
        item.get("variable")
        for item in by_id["escalation_end"]["data"].get("outputs") or []
    }
    expected_escalation_vars = {
        "escalation_initial_qa",
        "escalation_repair_route",
        "escalation_repair_validation",
        "escalation_qa_recheck",
    }
    if escalation_vars != expected_escalation_vars:
        fail(f"Escalation output mismatch: {sorted(escalation_vars)}")

    all_end_variables = []
    for end_id in ("final_end", "gate_failure_end", "repaired_end", "visual_repaired_final_end", "escalation_end"):
        all_end_variables.extend(
            item.get("variable")
            for item in by_id[end_id]["data"].get("outputs") or []
        )
    duplicates = sorted({
        variable
        for variable in all_end_variables
        if all_end_variables.count(variable) > 1
    })
    if duplicates:
        fail(f"End output variables must be globally unique: {duplicates}")

    serialized = path.read_text(encoding="utf-8")
    forbidden_literals = ["DIFY_API_KEY", "OPENAI_API_KEY", "sk-proj-", "Bearer "]
    leaked = [value for value in forbidden_literals if value in serialized]
    if leaked:
        fail(f"Secret-like literals must not be embedded in DSL: {leaked}")

    print(json.dumps({
        "status": "PASS",
        "dsl": str(path),
        "dsl_version": data["version"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(sorted(node_types.items())),
        "production_dataset_id": PRODUCTION_DATASET_ID,
        "phase4_wiring": True,
        "slide_gate": "deterministic",
        "visual_gate": "deterministic",
        "semantic_qa": True,
        "visual_gate_auto_repair": True,
        "studio_repair_passes": 1,
        "python_max_repair_cycles": 3,
        "model_provider": "langgenius/openai/openai",
        "model": "gpt-5.6-luna",
        "secret_leaks": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

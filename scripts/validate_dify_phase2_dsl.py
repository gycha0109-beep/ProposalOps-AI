#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_DSL = "dify/proposalops-phase2-core.yml"
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

    workflow = data.get("workflow") or {}
    graph = workflow.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes or not edges:
        fail("Workflow graph is empty.")

    by_id = {node.get("id"): node for node in nodes}
    if len(by_id) != len(nodes) or None in by_id:
        fail("Node IDs must be unique and non-null.")

    for edge in edges:
        if edge.get("source") not in by_id:
            fail(f"Edge source does not exist: {edge.get('source')}")
        if edge.get("target") not in by_id:
            fail(f"Edge target does not exist: {edge.get('target')}")

    node_types = Counter((node.get("data") or {}).get("type") for node in nodes)
    required_counts = {
        "start": 1,
        "llm": 4,
        "code": 5,
        "iteration": 1,
        "iteration-start": 1,
        "knowledge-retrieval": 1,
        "end": 1,
    }
    for node_type, count in required_counts.items():
        if node_types.get(node_type, 0) != count:
            fail(
                f"Unexpected {node_type} count: "
                f"{node_types.get(node_type, 0)} != {count}"
            )

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
        "end",
    }
    if set(by_id) != expected_ids:
        fail(
            "Unexpected node IDs. "
            f"missing={sorted(expected_ids - set(by_id))} "
            f"extra={sorted(set(by_id) - expected_ids)}"
        )

    iteration = by_id["query_iteration"]["data"]
    if iteration.get("is_parallel") is not False:
        fail("Query iteration must be serial for Sandbox rate-limit safety.")
    if iteration.get("iterator_input_type") != "array[string]":
        fail("Iteration input must be array[string].")
    if iteration.get("output_type") != "array[string]":
        fail("Iteration output must be array[string].")

    parse_code = by_id["parse_plans"]["data"].get("code", "")
    if "len(queries) != 2" not in parse_code or "len(set(queries)) != 2" not in parse_code:
        fail("Parse Plans must enforce exactly two distinct queries.")

    delay_code = by_id["rate_limit_delay"]["data"].get("code", "")
    if "time.sleep(7)" not in delay_code:
        fail("Sandbox rate-limit delay must remain 7 seconds.")

    knowledge = by_id["knowledge_retrieval"]["data"]
    dataset_ids = knowledge.get("dataset_ids") or []
    if dataset_ids != [PRODUCTION_DATASET_ID]:
        fail(f"Knowledge node must use production dataset only: {dataset_ids}")
    if BENCHMARK_DATASET_ID in dataset_ids:
        fail("Benchmark dataset must never be wired into production workflow.")
    if knowledge.get("retrieval_mode") != "multiple":
        fail("Knowledge node must use multiple retrieval mode.")
    if (knowledge.get("multiple_retrieval_config") or {}).get("top_k") != 5:
        fail("Knowledge top_k must be 5.")

    normalize_code = by_id["normalize_retrieval"]["data"].get("code", "")
    required_markers = [
        "INTENT_PAGE_TYPES",
        '"strategy": {"strategy", "target_analysis", "channel_plan"}',
        '"content": {"strategy", "content_plan", "channel_plan"}',
        '"kpi": {"kpi"}',
        "candidates[:5]",
    ]
    missing_markers = [marker for marker in required_markers if marker not in normalize_code]
    if missing_markers:
        fail(f"Normalize Retrieval is missing markers: {missing_markers}")

    for node_id in (
        "rfp_analyzer",
        "retrieval_planner",
        "evidence_builder",
        "proposal_strategist",
    ):
        model = by_id[node_id]["data"].get("model") or {}
        if model.get("provider") not in ("", None) or model.get("name") not in ("", None):
            fail(
                f"{node_id} must rely on workspace default model so the portable "
                "DSL does not pin stale plugin identifiers."
            )

    end_outputs = (by_id["end"]["data"].get("outputs") or [])
    end_vars = {item.get("variable") for item in end_outputs}
    expected_outputs = {
        "rfp_analysis",
        "retrieval_plan",
        "retrieval_trace",
        "evidence_packs",
        "proposal_strategy",
    }
    if end_vars != expected_outputs:
        fail(f"End outputs mismatch: {sorted(end_vars)}")

    serialized = path.read_text(encoding="utf-8")
    forbidden_literals = ["DIFY_API_KEY", "OPENAI_API_KEY", "sk-proj-", "Bearer "]
    leaked = [value for value in forbidden_literals if value in serialized]
    if leaked:
        fail(f"Secret-like literals must not be embedded in DSL: {leaked}")

    result = {
        "status": "PASS",
        "dsl": str(path),
        "dsl_version": data["version"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": dict(sorted(node_types.items())),
        "production_dataset_id": PRODUCTION_DATASET_ID,
        "serial_iteration": True,
        "dual_query_contract": True,
        "sandbox_delay_seconds": 7,
        "default_model_binding": True,
        "secret_leaks": 0,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

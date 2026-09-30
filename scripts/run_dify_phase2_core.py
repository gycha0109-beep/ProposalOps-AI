#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from lib.dify_knowledge import DifyError, DifyKnowledgeClient, asset_id_from_record
from lib.evidence_eval import evaluate_evidence_builder, load_corpus
from lib.openai_responses import ProviderError, call_openai_responses, get_openai_api_key
from lib.strategy_eval import evaluate_strategy


DEFAULT_CONFIG = "configs/dify-phase2-core-v1.json"

INTENT_PAGE_TYPES = {
    "strategy": {"strategy", "target_analysis", "channel_plan"},
    "content": {"strategy", "content_plan", "channel_plan"},
    "operation": {"operation_plan", "channel_plan"},
    "risk": {"operation_plan", "risk", "process"},
    "kpi": {"kpi"},
}


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def planner_contract():
    return r'''
Return JSON only:
{
  "plans": [
    {
      "requirement_id": "R-201",
      "intent": "strategy | content | operation | kpi | risk",
      "search_queries": ["semantic mechanism query", "anchor query preserving key nouns"],
      "filters": {},
      "must_find": ["..."],
      "nice_to_have": ["..."],
      "exclude": ["..."],
      "desired_evidence_count": 2
    }
  ]
}

Return exactly one plan per supplied RFP requirement.
Every plan must include exactly two non-empty, distinct search queries.
Query 1 must be a concise semantic description of the exact reusable mechanism needed.
Query 2 must preserve important nouns, formats, and action terms from the requirement while using a different phrasing.
Do not combine unrelated requirements into one plan.
'''


def evidence_contract():
    return r'''
Return JSON only:
{
  "results": [
    {
      "requirement_id": "R-201",
      "status": "SUPPORTED | PARTIAL_REFERENCE_ONLY | NO_REFERENCE_FOUND",
      "evidence": [
        {
          "evidence_id": "EV-R-201-01",
          "asset_id": "PA-...",
          "proposal_id": "PROP-...",
          "title": "exact candidate.title value",
          "supported_point": "what this source actually supports",
          "reusable_patterns": ["..."],
          "company_facts": [],
          "support_level": "direct | partial | pattern_only",
          "allowed_use": "REFERENCE_FACT | REFERENCE_PATTERN",
          "prohibited_use": "what must not be claimed from this evidence",
          "source": {
            "file_name": "exact source file",
            "page": 1,
            "source_type": "exact source type"
          }
        }
      ]
    }
  ]
}

Return exactly one result per supplied requirement.
Evidence IDs must be sequential within each requirement.
Do not select irrelevant candidates merely to fill a quota.\nFor title, copy the candidate.title field exactly. Do not use candidate.document_name.
'''


def strategist_contract():
    return r'''
Return JSON only using this top-level contract:
{
  "proposal_thesis": "string",
  "concept": "string",
  "strategy_pillars": [
    {
      "strategy_id": "ST-01",
      "pillar": "string",
      "description": "string",
      "requirement_ids": ["R-201"],
      "classification": "RFP_FACT | REFERENCE_FACT | REFERENCE_PATTERN | AI_RECOMMENDATION",
      "evidence_ids": ["EV-R-201-01"]
    }
  ],
  "information_classes": {
    "RFP_FACT": [],
    "REFERENCE_FACT": [],
    "REFERENCE_PATTERN": [],
    "AI_RECOMMENDATION": []
  },
  "reference_gaps": [
    {
      "requirement_id": "R-201",
      "gap": "string",
      "response": "string"
    }
  ]
}

Every RFP requirement must be covered by at least one strategy pillar.
Use only evidence IDs supplied in the Evidence Pack.
'''


def validate_plans(rfp_analysis: dict, planner: dict):
    required = [item["id"] for item in rfp_analysis.get("requirements", [])]
    rows = planner.get("plans", []) if isinstance(planner, dict) else []
    by_req = {row.get("requirement_id"): row for row in rows if isinstance(row, dict)}
    missing = [rid for rid in required if rid not in by_req]
    invalid = []
    for rid in required:
        row = by_req.get(rid)
        if not row:
            continue
        queries = row.get("search_queries")
        normalized_queries = (
            [query.strip() for query in queries if isinstance(query, str) and query.strip()]
            if isinstance(queries, list)
            else []
        )
        if len(normalized_queries) != 2 or len(set(normalized_queries)) != 2:
            invalid.append(rid)
    extras = sorted(set(by_req) - set(required))
    return {
        "required_count": len(required),
        "plan_count": len(rows),
        "missing_requirement_ids": missing,
        "invalid_query_requirement_ids": invalid,
        "unexpected_requirement_ids": extras,
        "pass": not missing and not invalid and not extras and len(rows) == len(required),
    }


def retrieve_candidates(
    client,
    dataset_id,
    plans,
    corpus,
    top_k,
    search_method,
    queries_per_requirement,
):
    results = []
    for plan in plans:
        all_queries = [
            query.strip()
            for query in plan.get("search_queries", [])
            if isinstance(query, str) and query.strip()
        ]
        queries = all_queries[:queries_per_requirement]
        merged = {}
        unknown = []

        for query_index, query in enumerate(queries, start=1):
            response = client.retrieve(
                dataset_id,
                query,
                top_k=top_k,
                search_method=search_method,
            )
            for rank, record in enumerate(response.get("records", []), start=1):
                asset_id = asset_id_from_record(record)
                if not asset_id or asset_id not in corpus:
                    unknown.append({
                        "query_index": query_index,
                        "query": query,
                        "rank": rank,
                        "asset_id": asset_id,
                        "segment_id": (record.get("segment") or {}).get("id"),
                    })
                    continue

                score = float(record.get("score") or 0.0)
                row = merged.get(asset_id)
                if row is None:
                    doc = corpus[asset_id]
                    document_name = doc["name"]
                    title = (
                        document_name.split("__", 1)[1]
                        if "__" in document_name
                        else document_name
                    )
                    row = {
                        "retrieval_rank": rank,
                        "retrieval_score": score,
                        "asset_id": asset_id,
                        "title": title,
                        "document_name": document_name,
                        "text": doc["text"],
                        "metadata": doc["metadata"],
                        "matched_queries": [],
                    }
                    merged[asset_id] = row
                elif score > float(row.get("retrieval_score") or 0.0):
                    row["retrieval_score"] = score
                    row["retrieval_rank"] = rank

                row["matched_queries"].append({
                    "query_index": query_index,
                    "query": query,
                    "rank": rank,
                    "score": score,
                })

        raw_candidates = sorted(
            merged.values(),
            key=lambda item: (-float(item.get("retrieval_score") or 0.0), item["asset_id"]),
        )

        intent = str(plan.get("intent") or "").strip().lower()
        allowed_page_types = INTENT_PAGE_TYPES.get(intent)
        if allowed_page_types:
            eligible = [
                item for item in raw_candidates
                if (item.get("metadata") or {}).get("page_type") in allowed_page_types
            ]
        else:
            eligible = raw_candidates

        candidates = eligible[:top_k]
        selected_ids = {item["asset_id"] for item in candidates}
        filtered_out = [
            item["asset_id"] for item in raw_candidates
            if item["asset_id"] not in selected_ids
        ]

        results.append({
            "requirement_id": plan["requirement_id"],
            "intent": plan.get("intent"),
            "query": " || ".join(queries),
            "queries": queries,
            "allowed_page_types": sorted(allowed_page_types) if allowed_page_types else [],
            "filtered_out_asset_ids": filtered_out,
            "candidates": candidates,
            "unknown_records": unknown,
        })
    return results


def integration_evidence_gold(strategy_gold: dict):
    cases = []
    for row in strategy_gold["evidence_expectations"]:
        allowed = list(row["allowed_asset_ids"])
        cases.append({
            "requirement_id": row["requirement_id"],
            "expected_status": "SUPPORTED",
            "primary_asset_ids": allowed,
            "accepted_asset_ids": allowed,
            "forbidden_asset_ids": [],
        })
    return {
        "version": "phase2-integration",
        "split": "dev",
        "track": "evidence_builder",
        "acceptance": {
            "result_coverage": 1.0,
            "primary_asset_recall": 1.0,
            "selected_asset_precision": 1.0,
            "prohibited_asset_rejection": 1.0,
            "provenance_validity": 1.0,
            "status_accuracy": 1.0,
            "company_fact_violation_count": 0,
            "unsupported_numeric_claim_count": 0,
        },
        "cases": cases,
    }


def build_provenance(strategy: dict, evidence_packs: list[dict]):
    evidence_map = {}
    for pack in evidence_packs:
        for evidence in pack.get("evidence", []):
            evidence_id = evidence.get("evidence_id")
            if evidence_id:
                evidence_map[evidence_id] = evidence

    chains = []
    broken = []
    for pillar in strategy.get("strategy_pillars", []):
        strategy_id = pillar.get("strategy_id")
        requirements = pillar.get("requirement_ids", [])
        evidence_ids = pillar.get("evidence_ids", [])
        if not isinstance(requirements, list):
            requirements = []
        if not isinstance(evidence_ids, list):
            evidence_ids = []

        for requirement_id in requirements:
            if not evidence_ids:
                row = {
                    "requirement_id": requirement_id,
                    "evidence_id": None,
                    "asset_id": None,
                    "strategy_id": strategy_id,
                    "valid": False,
                }
                chains.append(row)
                broken.append(row)
                continue

            for evidence_id in evidence_ids:
                evidence = evidence_map.get(evidence_id)
                row = {
                    "requirement_id": requirement_id,
                    "evidence_id": evidence_id,
                    "asset_id": evidence.get("asset_id") if evidence else None,
                    "strategy_id": strategy_id,
                    "valid": evidence is not None,
                }
                chains.append(row)
                if not row["valid"]:
                    broken.append(row)

    return {
        "chains": chains,
        "broken_chains": broken,
        "pass": not broken,
    }


def render_markdown(result: dict):
    evidence_metrics = result["validation"]["evidence_builder"]["metrics"]
    strategy_metrics = result["validation"]["proposal_strategist"]["metrics"]
    lines = [
        "# Dify Phase 2 Core — RFP-TEST-002",
        "",
        "- status: " + result["status"],
        "- Dify dataset: " + result["dify"]["dataset_id"],
        "- retrieval: " + result["dify"]["search_method"] + " top-" + str(result["dify"]["top_k"]),
        "",
        "## Stage result",
        "",
        "- RFP Analyzer: " + ("PASS" if result["validation"]["rfp_analyzer_pass"] else "FAIL"),
        "- Retrieval Planner: " + ("PASS" if result["validation"]["retrieval_planner"]["pass"] else "FAIL"),
        "- Evidence Builder: " + ("PASS" if result["validation"]["evidence_builder"]["pass"] else "FAIL"),
        "- Proposal Strategist: " + ("PASS" if result["validation"]["proposal_strategist_pass"] else "FAIL"),
        "- Provenance chain: " + ("PASS" if result["validation"]["provenance"]["pass"] else "FAIL"),
        "",
        "## Evidence Builder",
        "",
        "- result coverage: {:.2%}".format(evidence_metrics["result_coverage"]),
        "- primary asset recall: {:.2%}".format(evidence_metrics["primary_asset_recall"]),
        "- selected asset precision: {:.2%}".format(evidence_metrics["selected_asset_precision"]),
        "- provenance validity: {:.2%}".format(evidence_metrics["provenance_validity"]),
        "",
        "## Proposal Strategist",
        "",
        "- requirement coverage: {:.2%}".format(strategy_metrics["requirement_coverage"]),
        "- evidence citation coverage: {:.2%}".format(strategy_metrics["evidence_citation_coverage"]),
        "- evidence validity: {:.2%}".format(strategy_metrics["evidence_validity"]),
        "- unsupported company claims: {}".format(strategy_metrics["unsupported_company_claim_count"]),
        "- unsupported quantitative claims: {}".format(strategy_metrics["unsupported_quantitative_claim_count"]),
        "- invalid evidence refs: {}".format(strategy_metrics["invalid_evidence_reference_count"]),
        "",
        "## Retrieval trace",
        "",
    ]
    for row in result["retrieval_results"]:
        asset_ids = [item["asset_id"] for item in row["candidates"]]
        lines.append(
            "- {}: {} -> {}".format(
                row["requirement_id"],
                row["query"],
                ", ".join(asset_ids),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    plan = {
        "phase": "dify-phase2-core",
        "rfp_id": config["rfp_id"],
        "model": config["model"],
        "openai_calls": 4,
        "dify_retrieval_calls": 6 * int(config["dify"].get("queries_per_requirement", 1)),
        "dataset_id": config["dify"]["production_dataset_id"],
        "search_method": config["dify"]["search_method"],
        "top_k": config["dify"]["top_k"],
        "output_root": config["output_root"],
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    api_key = get_openai_api_key()
    dify_key = os.environ.get("DIFY_API_KEY", "").strip()
    if not dify_key:
        raise SystemExit("DIFY_API_KEY is required.")

    rfp_text = Path(config["rfp_file"]).read_text(encoding="utf-8")
    corpus = load_corpus(config["corpus"])
    stage_metadata = {}

    rfp_analysis, stage_metadata["rfp_analyzer"] = call_stage(
        api_key,
        config,
        "rfp_analyzer",
        prompt_text(config["prompts"]["rfp_analyzer"]),
        {"rfp_id": config["rfp_id"], "rfp_text": rfp_text},
    )

    planner, stage_metadata["retrieval_planner"] = call_stage(
        api_key,
        config,
        "retrieval_planner",
        prompt_text(config["prompts"]["retrieval_planner"]) + "\n\n" + planner_contract(),
        {"rfp_id": config["rfp_id"], "rfp_analysis": rfp_analysis},
    )
    planner_check = validate_plans(rfp_analysis, planner)
    if not planner_check["pass"]:
        raise SystemExit(
            "Retrieval Planner contract failed: "
            + json.dumps(planner_check, ensure_ascii=False)
        )

    dify = DifyKnowledgeClient(
        api_key=dify_key,
        api_base=config["dify"]["api_base"],
        min_interval_seconds=float(config["dify"]["delay_seconds"]),
    )
    retrieval_results = retrieve_candidates(
        dify,
        config["dify"]["production_dataset_id"],
        planner["plans"],
        corpus,
        int(config["dify"]["top_k"]),
        config["dify"]["search_method"],
        int(config["dify"].get("queries_per_requirement", 1)),
    )
    if any(row["unknown_records"] for row in retrieval_results):
        raise SystemExit("Dify retrieval returned unknown assets.")

    requirements = {
        item["id"]: item
        for item in rfp_analysis.get("requirements", [])
    }
    evidence_cases = [
        {
            "requirement": requirements[row["requirement_id"]],
            "retrieval_query": row["query"],
            "candidates": row["candidates"],
        }
        for row in retrieval_results
    ]

    evidence_output, stage_metadata["evidence_builder"] = call_stage(
        api_key,
        config,
        "evidence_builder",
        prompt_text(config["prompts"]["evidence_builder"]) + "\n\n" + evidence_contract(),
        {
            "task": "Build safe evidence packs for each RFP requirement independently.",
            "rfp_id": config["rfp_id"],
            "cases": evidence_cases,
        },
    )
    evidence_packs = evidence_output.get("results", [])

    strategist_gold = load_json(config["strategist_gold"])
    evidence_gold = integration_evidence_gold(strategist_gold)
    evidence_evaluation = evaluate_evidence_builder(
        {"results": evidence_packs},
        evidence_gold,
        corpus,
    )

    strategy, stage_metadata["proposal_strategist"] = call_stage(
        api_key,
        config,
        "proposal_strategist",
        prompt_text(config["prompts"]["proposal_strategist"]) + "\n\n" + strategist_contract(),
        {
            "rfp_id": config["rfp_id"],
            "rfp_text": rfp_text,
            "rfp_analysis": rfp_analysis,
            "evidence_packs": evidence_packs,
        },
    )
    strategy_evaluation = evaluate_strategy(
        strategy,
        strategist_gold,
        {"evidence_packs": evidence_packs},
    )
    strategy_metrics = strategy_evaluation["metrics"]
    strategy_pass = (
        strategy_metrics["requirement_coverage"] == 1.0
        and strategy_metrics["evidence_citation_coverage"] == 1.0
        and strategy_metrics["evidence_validity"] == 1.0
        and strategy_metrics["unsupported_company_claim_count"] == 0
        and strategy_metrics["unsupported_quantitative_claim_count"] == 0
        and strategy_metrics["information_class_separation"] == 1.0
        and strategy_metrics["invalid_evidence_reference_count"] == 0
    )

    provenance = build_provenance(strategy, evidence_packs)

    required_ids = {
        item["id"]
        for item in rfp_analysis.get("requirements", [])
    }
    analyzer_pass = required_ids == set(strategist_gold["required_requirement_ids"])

    status = "PASS" if (
        analyzer_pass
        and planner_check["pass"]
        and evidence_evaluation["pass"]
        and strategy_pass
        and provenance["pass"]
    ) else "FAIL"

    result = {
        "version": config["version"],
        "phase": "dify-phase2-core",
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rfp_id": config["rfp_id"],
        "model": config["model"],
        "dify": {
            "dataset_id": config["dify"]["production_dataset_id"],
            "search_method": config["dify"]["search_method"],
            "top_k": config["dify"]["top_k"],
        },
        "rfp_analysis": rfp_analysis,
        "retrieval_plans": planner["plans"],
        "retrieval_results": retrieval_results,
        "evidence_packs": evidence_packs,
        "proposal_strategy": strategy,
        "validation": {
            "rfp_analyzer_pass": analyzer_pass,
            "retrieval_planner": planner_check,
            "evidence_builder": evidence_evaluation,
            "proposal_strategist": strategy_evaluation,
            "proposal_strategist_pass": strategy_pass,
            "provenance": provenance,
        },
        "stage_metadata": stage_metadata,
    }

    root = Path(config["output_root"])
    root.mkdir(parents=True, exist_ok=True)
    (root / "core-workflow.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report_json = Path(config["report_json"])
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report_md = Path(config["report_md"])
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(render_markdown(result), encoding="utf-8")

    print(json.dumps({
        "status": status,
        "rfp_id": config["rfp_id"],
        "planner": planner_check,
        "evidence_metrics": evidence_evaluation["metrics"],
        "strategy_metrics": strategy_evaluation["metrics"],
        "broken_provenance_chains": len(provenance["broken_chains"]),
        "report": config["report_json"],
    }, ensure_ascii=False, indent=2))

    if status != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    try:
        main()
    except (ProviderError, DifyError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

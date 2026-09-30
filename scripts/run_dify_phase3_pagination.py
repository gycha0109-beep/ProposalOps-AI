#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from lib.openai_responses import ProviderError, call_openai_responses, get_openai_api_key
from lib.pagination_eval import validate_pagination


DEFAULT_CONFIG = "configs/dify-phase3-pagination-v1.json"


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


def render_markdown(result: dict):
    validation = result["coverage_validation"]
    lines = [
        "# Dify Phase 3 — Pagination + Coverage Gate",
        "",
        f'- RFP: {result["rfp_id"]}',
        f'- status: **{result["status"]}**',
        f'- model: {result["model"]}',
        f'- pages: **{len(result["pagination"].get("pages", []))}** / limit {result["page_limit"]}',
        "",
        "## Coverage",
        "",
        f'- requirements: **{validation["coverage_summary"]["total_requirements"]}**',
        f'- covered: **{validation["coverage_summary"]["covered"]}**',
        f'- missing: **{validation["coverage_summary"]["missing"]}**',
        f'- blocking errors: **{len(validation["blocking_errors"])}**',
        f'- warnings: **{len(validation["warnings"])}**',
        "",
        "## Requirement → Page",
        "",
    ]

    for requirement_id, page_ids in validation["requirement_page_map"].items():
        lines.append(f'- {requirement_id}: {", ".join(page_ids) if page_ids else "MISSING"}')

    lines.extend([
        "",
        "## Page outline",
        "",
    ])
    for page in result["pagination"].get("pages", []):
        reqs = ", ".join(page.get("rfp_requirement_ids", [])) or "-"
        strategies = ", ".join(page.get("strategy_ids", [])) or "-"
        evidences = ", ".join(page.get("evidence_ids", [])) or "-"
        lines.append(
            f'- {page.get("page_id")} / {page.get("title")} '
            f'| req={reqs} | strategy={strategies} | evidence={evidences}'
        )

    if validation["blocking_errors"]:
        lines.extend(["", "## Blocking errors", ""])
        for error in validation["blocking_errors"]:
            lines.append(
                f'- {error["code"]} page={error.get("page_id")} '
                f'requirement={error.get("requirement_id")}: {error["reason"]}'
            )

    if validation["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in validation["warnings"]:
            lines.append(
                f'- {warning["code"]} page={warning.get("page_id")} '
                f'requirement={warning.get("requirement_id")}: {warning["reason"]}'
            )

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    config = load_json(args.config)
    source = load_json(config["source_report"])

    if source.get("status") != "PASS":
        raise SystemExit(
            f'Phase 2 source must be PASS, got {source.get("status")!r}: '
            f'{config["source_report"]}'
        )

    plan = {
        "phase": config["phase"],
        "rfp_id": config["rfp_id"],
        "model": config["model"],
        "source_report": config["source_report"],
        "page_limit": config["page_limit"],
        "openai_calls": 1,
        "coverage_validator": "deterministic_code_gate",
        "output_root": config["output_root"],
    }
    if args.plan_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    api_key = get_openai_api_key()
    prompt = prompt_text(config["pagination_prompt"]) + f"""

Integration constraints:
- Use at most {config["page_limit"]} pages.
- Use only supplied canonical requirement IDs, strategy IDs, and evidence IDs.
- If a page cites a REFERENCE_FACT or REFERENCE_PATTERN strategy, attach at least one evidence_id used by that strategy.
- A requirement-specific page must not cite evidence belonging to another requirement.
- requirement_coverage must be derived from the generated pages and must include every canonical requirement exactly once.
- Return JSON only using the Pagination Planner output contract.
"""

    response = call_openai_responses(
        api_key=api_key,
        model=config["model"],
        reasoning_effort=config["reasoning_effort"],
        max_output_tokens=config["max_output_tokens"],
        instructions=prompt,
        input_text=json.dumps({
            "rfp_id": config["rfp_id"],
            "rfp_analysis": source["rfp_analysis"],
            "proposal_strategy": source["proposal_strategy"],
            "evidence_packs": source["evidence_packs"],
            "page_limit": config["page_limit"],
        }, ensure_ascii=False, indent=2),
        max_retries=2,
        retry_delay_seconds=5,
    )

    pagination = parse_json(response["output_text"])
    coverage = validate_pagination(
        pagination,
        source["rfp_analysis"],
        source["proposal_strategy"],
        source["evidence_packs"],
        page_limit=int(config["page_limit"]),
    )

    status = coverage["status"]
    result = {
        "version": config["version"],
        "phase": config["phase"],
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rfp_id": config["rfp_id"],
        "model": response["model"],
        "reasoning_effort": config["reasoning_effort"],
        "source_report": config["source_report"],
        "page_limit": config["page_limit"],
        "pagination": pagination,
        "coverage_validation": coverage,
        "stage_metadata": {
            "provider": response["provider"],
            "response_id": response["response_id"],
            "latency_seconds": response["latency_seconds"],
            "retry_count": response.get("retry_count", 0),
            "usage": response.get("usage", {}),
        },
    }

    root = Path(config["output_root"])
    root.mkdir(parents=True, exist_ok=True)
    (root / "pagination.json").write_text(
        json.dumps(pagination, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "coverage-validation.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "phase3-result.json").write_text(
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
        "page_count": len(pagination.get("pages", [])),
        "coverage_summary": coverage["coverage_summary"],
        "blocking_error_count": len(coverage["blocking_errors"]),
        "warning_count": len(coverage["warnings"]),
        "report": config["report_json"],
    }, ensure_ascii=False, indent=2))

    if status != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    try:
        main()
    except (ProviderError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

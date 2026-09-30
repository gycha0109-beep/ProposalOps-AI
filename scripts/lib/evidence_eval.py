from __future__ import annotations

import json
import re
from pathlib import Path


EVIDENCE_ID_RE = re.compile(r"^EV-(R-\d+)-\d{2}$")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?(?:%|명|건|편|원|초|개월|회)?")


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_corpus(path: str) -> dict[str, dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return {row["asset_id"]: row for row in rows}


def parse_evidence_output(raw: str) -> dict | None:
    text = raw.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def expected_title(doc: dict) -> str:
    name = str(doc.get("name") or "")
    if "__" in name:
        return name.split("__", 1)[1]
    return name


def source_matches(evidence: dict, doc: dict) -> bool:
    meta = doc.get("metadata") or {}
    source = evidence.get("source") or {}
    return (
        evidence.get("proposal_id") == meta.get("proposal_id")
        and evidence.get("title") == expected_title(doc)
        and source.get("file_name") == meta.get("source_file")
        and source.get("page") == meta.get("source_page")
        and source.get("source_type") == meta.get("source_type")
    )


def unsupported_numbers(evidence: dict, doc: dict) -> list[str]:
    text = str(doc.get("text") or "")
    fields = [
        str(evidence.get("supported_point") or ""),
        " ".join(str(x) for x in (evidence.get("company_facts") or [])),
    ]
    values = []
    for field in fields:
        for token in NUMBER_RE.findall(field):
            if token and token not in text:
                values.append(token)
    return sorted(set(values))


def unsupported_company_facts(evidence: dict, doc: dict) -> list[str]:
    text = str(doc.get("text") or "")
    bad = []
    for fact in evidence.get("company_facts") or []:
        value = str(fact).strip()
        if value and value not in text:
            bad.append(value)
    return bad


def evaluate_evidence_builder(output: dict, gold: dict, corpus: dict[str, dict]) -> dict:
    rows = output.get("results", []) if isinstance(output, dict) else []
    rows = [row for row in rows if isinstance(row, dict)]
    by_req = {row.get("requirement_id"): row for row in rows if row.get("requirement_id")}

    case_results = []
    selected_total = 0
    selected_accepted = 0
    primary_hits = 0
    prohibited_case_passes = 0
    provenance_total = 0
    provenance_valid = 0
    status_hits = 0
    company_fact_violations = 0
    numeric_violations = 0
    evidence_id_violations = 0

    for case in gold["cases"]:
        requirement_id = case["requirement_id"]
        row = by_req.get(requirement_id)
        accepted = set(case["accepted_asset_ids"])
        primary = set(case["primary_asset_ids"])
        forbidden = set(case.get("forbidden_asset_ids", []))

        if not row:
            case_results.append({
                "requirement_id": requirement_id,
                "found": False,
                "status_match": False,
                "primary_hit": False,
                "selected_asset_ids": [],
                "unexpected_asset_ids": [],
                "prohibited_asset_ids": [],
                "provenance_valid": False,
                "company_fact_violations": [],
                "unsupported_numbers": [],
                "evidence_id_violations": [],
            })
            continue

        status_match = row.get("status") == case["expected_status"]
        status_hits += int(status_match)

        evidence_rows = row.get("evidence", [])
        if not isinstance(evidence_rows, list):
            evidence_rows = []

        selected_ids = []
        unexpected = []
        prohibited = []
        provenance_flags = []
        company_bad = []
        numeric_bad = []
        id_bad = []

        for evidence in evidence_rows:
            if not isinstance(evidence, dict):
                continue
            asset_id = evidence.get("asset_id")
            if not asset_id:
                continue

            selected_ids.append(asset_id)
            selected_total += 1
            if asset_id in accepted:
                selected_accepted += 1
            else:
                unexpected.append(asset_id)

            doc = corpus.get(asset_id)
            meta = (doc or {}).get("metadata") or {}
            is_prohibited = (
                asset_id in forbidden
                or str(asset_id).startswith("PA-DIST-")
                or meta.get("reuse_level") == "prohibited"
                or meta.get("proposal_id") == "DISTRACTOR-REF"
            )
            if is_prohibited:
                prohibited.append(asset_id)

            provenance_total += 1
            prov_ok = bool(doc) and source_matches(evidence, doc)
            provenance_valid += int(prov_ok)
            provenance_flags.append(prov_ok)

            evidence_id = str(evidence.get("evidence_id") or "")
            match = EVIDENCE_ID_RE.match(evidence_id)
            if not match or match.group(1) != requirement_id:
                evidence_id_violations += 1
                id_bad.append(evidence_id)

            if doc:
                cf_bad = unsupported_company_facts(evidence, doc)
                num_bad = unsupported_numbers(evidence, doc)
            else:
                cf_bad = [str(x) for x in evidence.get("company_facts") or []]
                num_bad = []
            company_fact_violations += len(cf_bad)
            numeric_violations += len(num_bad)
            company_bad.extend(cf_bad)
            numeric_bad.extend(num_bad)

        primary_hit = any(asset_id in primary for asset_id in selected_ids)
        primary_hits += int(primary_hit)
        prohibited_pass = not prohibited
        prohibited_case_passes += int(prohibited_pass)

        case_results.append({
            "requirement_id": requirement_id,
            "found": True,
            "status_match": status_match,
            "primary_hit": primary_hit,
            "selected_asset_ids": selected_ids,
            "unexpected_asset_ids": sorted(set(unexpected)),
            "prohibited_asset_ids": sorted(set(prohibited)),
            "provenance_valid": all(provenance_flags) if provenance_flags else False,
            "company_fact_violations": company_bad,
            "unsupported_numbers": sorted(set(numeric_bad)),
            "evidence_id_violations": id_bad,
        })

    total_cases = len(gold["cases"])
    coverage = sum(int(row["found"]) for row in case_results) / total_cases if total_cases else 0.0
    metrics = {
        "result_coverage": round(coverage, 4),
        "primary_asset_recall": round(primary_hits / total_cases, 4) if total_cases else 0.0,
        "selected_asset_precision": round(selected_accepted / selected_total, 4) if selected_total else 0.0,
        "prohibited_asset_rejection": round(prohibited_case_passes / total_cases, 4) if total_cases else 0.0,
        "provenance_validity": round(provenance_valid / provenance_total, 4) if provenance_total else 0.0,
        "status_accuracy": round(status_hits / total_cases, 4) if total_cases else 0.0,
        "company_fact_violation_count": company_fact_violations,
        "unsupported_numeric_claim_count": numeric_violations,
        "evidence_id_violation_count": evidence_id_violations,
    }

    acceptance = gold["acceptance"]
    passed = (
        metrics["result_coverage"] >= acceptance["result_coverage"]
        and metrics["primary_asset_recall"] >= acceptance["primary_asset_recall"]
        and metrics["selected_asset_precision"] >= acceptance["selected_asset_precision"]
        and metrics["prohibited_asset_rejection"] >= acceptance["prohibited_asset_rejection"]
        and metrics["provenance_validity"] >= acceptance["provenance_validity"]
        and metrics["status_accuracy"] >= acceptance["status_accuracy"]
        and metrics["company_fact_violation_count"] <= acceptance["company_fact_violation_count"]
        and metrics["unsupported_numeric_claim_count"] <= acceptance["unsupported_numeric_claim_count"]
        and metrics["evidence_id_violation_count"] == 0
    )

    return {
        "track": "evidence_builder",
        "evaluator_version": "1.0",
        "gold_version": gold["version"],
        "split": gold["split"],
        "metrics": metrics,
        "cases": case_results,
        "pass": passed,
    }

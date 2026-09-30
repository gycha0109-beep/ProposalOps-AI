from __future__ import annotations

import re


def _list(value):
    return value if isinstance(value, list) else []


def _norm_message(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def evidence_index(evidence_packs: list[dict]) -> dict[str, dict]:
    result = {}
    for pack in evidence_packs:
        requirement_id = pack.get("requirement_id")
        for evidence in _list(pack.get("evidence")):
            evidence_id = evidence.get("evidence_id")
            if not evidence_id:
                continue
            result[evidence_id] = {
                "requirement_id": requirement_id,
                "asset_id": evidence.get("asset_id"),
                "evidence": evidence,
            }
    return result


def strategy_index(strategy: dict) -> dict[str, dict]:
    result = {}
    for pillar in _list(strategy.get("strategy_pillars")):
        strategy_id = pillar.get("strategy_id")
        if strategy_id:
            result[strategy_id] = pillar
    return result


def validate_pagination(
    pagination: dict,
    rfp_analysis: dict,
    strategy: dict,
    evidence_packs: list[dict],
    *,
    page_limit: int | None = None,
) -> dict:
    pages = _list(pagination.get("pages"))
    requirements = {
        item.get("id"): item
        for item in _list(rfp_analysis.get("requirements"))
        if item.get("id")
    }
    strategies = strategy_index(strategy)
    evidences = evidence_index(evidence_packs)

    blocking_errors = []
    warnings = []
    covered_by = {requirement_id: [] for requirement_id in requirements}
    seen_page_ids = set()
    seen_numbers = set()
    message_to_pages: dict[str, list[str]] = {}

    def block(code, *, page_id=None, requirement_id=None, reason, action):
        blocking_errors.append({
            "code": code,
            "page_id": page_id,
            "requirement_id": requirement_id,
            "reason": reason,
            "action": action,
        })

    def warn(code, *, page_id=None, requirement_id=None, reason, action):
        warnings.append({
            "code": code,
            "page_id": page_id,
            "requirement_id": requirement_id,
            "reason": reason,
            "action": action,
        })

    if not pages:
        block(
            "NO_PAGES",
            reason="Pagination output contains no pages.",
            action="Generate at least one proposal page.",
        )

    if page_limit is not None and len(pages) > page_limit:
        block(
            "PAGE_LIMIT_EXCEEDED",
            reason=f"Generated {len(pages)} pages but the limit is {page_limit}.",
            action="Compress or merge page structure without dropping mandatory requirements.",
        )

    for index, page in enumerate(pages, start=1):
        page_id = page.get("page_id")
        page_no = page.get("page_no")

        if not page_id:
            block(
                "MISSING_PAGE_ID",
                reason=f"Page at position {index} has no page_id.",
                action="Assign sequential PAGE-### identifiers.",
            )
            page_id = f"<position-{index}>"
        elif page_id in seen_page_ids:
            block(
                "DUPLICATE_PAGE_ID",
                page_id=page_id,
                reason="page_id is duplicated.",
                action="Use a unique sequential page_id.",
            )
        seen_page_ids.add(page_id)

        if page_no != index:
            block(
                "NON_SEQUENTIAL_PAGE_NO",
                page_id=page_id,
                reason=f"Expected page_no {index}, got {page_no}.",
                action="Renumber pages sequentially from 1.",
            )
        if page_no in seen_numbers:
            block(
                "DUPLICATE_PAGE_NO",
                page_id=page_id,
                reason=f"page_no {page_no} is duplicated.",
                action="Use unique sequential page numbers.",
            )
        seen_numbers.add(page_no)

        for field in ("section", "page_type", "title", "page_goal", "key_message"):
            if not str(page.get(field) or "").strip():
                block(
                    "MISSING_PAGE_FIELD",
                    page_id=page_id,
                    reason=f"Required page field is empty: {field}.",
                    action=f"Provide a concrete {field}.",
                )

        requirement_ids = _list(page.get("rfp_requirement_ids"))
        strategy_ids = _list(page.get("strategy_ids"))
        evidence_ids = _list(page.get("evidence_ids"))

        if len(requirement_ids) > 2:
            warn(
                "REQUIREMENT_DENSITY",
                page_id=page_id,
                reason=f"Page mixes {len(requirement_ids)} requirements.",
                action="Consider splitting unrelated objectives across pages.",
            )

        for requirement_id in requirement_ids:
            if requirement_id not in requirements:
                block(
                    "INVALID_REQUIREMENT_ID",
                    page_id=page_id,
                    requirement_id=requirement_id,
                    reason="Page references a requirement that is not in the RFP analysis.",
                    action="Use only canonical RFP requirement IDs.",
                )
            else:
                covered_by[requirement_id].append(page_id)

        for strategy_id in strategy_ids:
            pillar = strategies.get(strategy_id)
            if pillar is None:
                block(
                    "INVALID_STRATEGY_ID",
                    page_id=page_id,
                    reason=f"Unknown strategy_id: {strategy_id}.",
                    action="Use only strategy IDs from Proposal Strategist.",
                )
                continue

            pillar_requirements = set(_list(pillar.get("requirement_ids")))
            if requirement_ids and not (pillar_requirements & set(requirement_ids)):
                block(
                    "STRATEGY_PAGE_MISMATCH",
                    page_id=page_id,
                    reason=(
                        f"{strategy_id} covers {sorted(pillar_requirements)} but page "
                        f"references {sorted(requirement_ids)}."
                    ),
                    action="Attach the strategy to a page covering the same RFP requirement.",
                )

            classification = pillar.get("classification")
            pillar_evidence = set(_list(pillar.get("evidence_ids")))
            if classification in {"REFERENCE_FACT", "REFERENCE_PATTERN"}:
                if not (pillar_evidence & set(evidence_ids)) and requirement_ids:
                    block(
                        "STRATEGY_EVIDENCE_MISSING",
                        page_id=page_id,
                        reason=(
                            f"{strategy_id} is {classification} but none of its evidence IDs "
                            "are attached to the page."
                        ),
                        action="Attach at least one valid evidence ID used by the strategy.",
                    )

        for evidence_id in evidence_ids:
            evidence = evidences.get(evidence_id)
            if evidence is None:
                block(
                    "INVALID_EVIDENCE_ID",
                    page_id=page_id,
                    reason=f"Unknown evidence_id: {evidence_id}.",
                    action="Use only Evidence Builder IDs.",
                )
                continue

            evidence_requirement = evidence.get("requirement_id")
            if requirement_ids and evidence_requirement not in requirement_ids:
                block(
                    "EVIDENCE_PAGE_MISMATCH",
                    page_id=page_id,
                    requirement_id=evidence_requirement,
                    reason=(
                        f"{evidence_id} belongs to {evidence_requirement}, not to the "
                        f"page requirements {sorted(requirement_ids)}."
                    ),
                    action="Move the evidence to the matching requirement page.",
                )

        if not requirement_ids and evidence_ids:
            block(
                "ORPHAN_EVIDENCE",
                page_id=page_id,
                reason="Page has evidence IDs but no RFP requirement IDs.",
                action="Link the page to the supported requirement or remove the evidence.",
            )

        fact_risk = str(page.get("fact_risk") or "").lower()
        if fact_risk == "high" and not evidence_ids:
            warn(
                "HIGH_FACT_RISK_WITHOUT_EVIDENCE",
                page_id=page_id,
                reason="fact_risk is high but the page has no evidence.",
                action="Add evidence or rewrite factual claims as recommendations.",
            )

        content_blocks = _list(page.get("content_blocks"))
        if not content_blocks:
            block(
                "NO_CONTENT_BLOCKS",
                page_id=page_id,
                reason="Page has no content_blocks.",
                action="Provide at least one content block describing slide intent.",
            )

        normalized_message = _norm_message(page.get("key_message"))
        if normalized_message:
            message_to_pages.setdefault(normalized_message, []).append(page_id)

    missing = [
        requirement_id
        for requirement_id, page_ids in covered_by.items()
        if not page_ids
    ]
    for requirement_id in missing:
        block(
            "MISSING_REQUIREMENT",
            requirement_id=requirement_id,
            reason="Mandatory RFP requirement is not connected to any page.",
            action="Create or revise a page so the requirement is explicitly covered.",
        )

    for page_ids in message_to_pages.values():
        if len(page_ids) > 1:
            warn(
                "DUPLICATE_KEY_MESSAGE",
                reason=f"Same key_message appears on pages {page_ids}.",
                action="Differentiate page messages or remove redundant pages.",
            )

    declared_rows = _list(pagination.get("requirement_coverage"))
    declared = {
        row.get("requirement_id"): row
        for row in declared_rows
        if isinstance(row, dict) and row.get("requirement_id")
    }
    for requirement_id in requirements:
        row = declared.get(requirement_id)
        expected_pages = covered_by[requirement_id]
        if row is None:
            block(
                "MISSING_COVERAGE_ROW",
                requirement_id=requirement_id,
                reason="requirement_coverage is missing a canonical requirement.",
                action="Add a coverage row derived from generated pages.",
            )
            continue

        declared_pages = sorted(_list(row.get("page_ids")))
        if declared_pages != sorted(expected_pages):
            block(
                "COVERAGE_SUMMARY_MISMATCH",
                requirement_id=requirement_id,
                reason=(
                    f"Declared pages {declared_pages} do not match actual pages "
                    f"{sorted(expected_pages)}."
                ),
                action="Recompute requirement_coverage from page references.",
            )

        expected_status = "COVERED" if expected_pages else "MISSING"
        if row.get("status") != expected_status:
            block(
                "COVERAGE_STATUS_MISMATCH",
                requirement_id=requirement_id,
                reason=(
                    f"Expected {expected_status}, got {row.get('status')}."
                ),
                action="Use COVERED only when at least one page references the requirement.",
            )

    extras = sorted(set(declared) - set(requirements))
    for requirement_id in extras:
        block(
            "INVALID_COVERAGE_REQUIREMENT",
            requirement_id=requirement_id,
            reason="requirement_coverage contains an unknown requirement ID.",
            action="Remove non-canonical requirement IDs.",
        )

    total = len(requirements)
    covered_count = total - len(missing)
    result = {
        "status": "PASS" if not blocking_errors else "FAIL",
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "coverage_summary": {
            "total_requirements": total,
            "covered": covered_count,
            "partial": 0,
            "missing": len(missing),
        },
        "page_count": len(pages),
        "page_limit": page_limit,
        "valid_strategy_ids": sorted(strategies),
        "valid_evidence_ids": sorted(evidences),
        "requirement_page_map": covered_by,
    }
    return result

from __future__ import annotations

import json
import re


ALLOWED_CLAIM_TYPES = {
    "RFP_FACT",
    "REFERENCE_FACT",
    "REFERENCE_PATTERN",
    "AI_RECOMMENDATION",
}
ALLOWED_VISUAL_TYPES = {
    "none",
    "icon_diagram",
    "process_diagram",
    "illustration",
    "photo",
    "data_chart",
    "reference_image",
}
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?(?:%|명|건|편|원|초|개월|회|개)?")


def _list(value):
    return value if isinstance(value, list) else []


def _numbers(text: str) -> set[str]:
    return {token for token in NUMBER_RE.findall(str(text or "")) if token}


def build_evidence_index(evidence_packs: list[dict]) -> dict[str, dict]:
    result = {}
    for pack in evidence_packs:
        requirement_id = pack.get("requirement_id")
        for evidence in _list(pack.get("evidence")):
            evidence_id = evidence.get("evidence_id")
            if evidence_id:
                result[evidence_id] = {
                    "requirement_id": requirement_id,
                    "asset_id": evidence.get("asset_id"),
                    "evidence": evidence,
                }
    return result


def _evidence_text(entry: dict) -> str:
    evidence = entry.get("evidence") or {}
    parts = [
        evidence.get("supported_point"),
        " ".join(str(x) for x in _list(evidence.get("reusable_patterns"))),
        " ".join(str(x) for x in _list(evidence.get("company_facts"))),
    ]
    return " ".join(str(x or "") for x in parts)


def validate_slides(
    slides_payload: dict,
    pagination: dict,
    rfp_analysis: dict,
    evidence_packs: list[dict],
) -> dict:
    pages = _list(pagination.get("pages"))
    slides = _list(slides_payload.get("slides"))
    page_by_id = {page.get("page_id"): page for page in pages if page.get("page_id")}
    evidence_index = build_evidence_index(evidence_packs)
    rfp_blob = json.dumps(rfp_analysis, ensure_ascii=False)

    errors = []
    warnings = []
    seen = set()
    slide_by_id = {}

    def block(code, page_id=None, reason="", action=""):
        errors.append({
            "code": code,
            "page_id": page_id,
            "reason": reason,
            "action": action,
        })

    def warn(code, page_id=None, reason="", action=""):
        warnings.append({
            "code": code,
            "page_id": page_id,
            "reason": reason,
            "action": action,
        })

    for slide in slides:
        page_id = slide.get("page_id")
        if not page_id:
            block("MISSING_PAGE_ID", reason="Slide has no page_id.")
            continue
        if page_id in seen:
            block("DUPLICATE_SLIDE", page_id=page_id, reason="Duplicate slide for page.")
            continue
        seen.add(page_id)
        slide_by_id[page_id] = slide

        page = page_by_id.get(page_id)
        if page is None:
            block("UNKNOWN_PAGE_ID", page_id=page_id, reason="Slide references a page not in Pagination.")
            continue

        if not str(slide.get("headline") or "").strip():
            block("MISSING_HEADLINE", page_id=page_id, reason="Slide headline is empty.")
        if not str(slide.get("subheadline") or "").strip():
            warn("MISSING_SUBHEADLINE", page_id=page_id, reason="Slide subheadline is empty.")

        visual_type = slide.get("visual_type")
        if visual_type not in ALLOWED_VISUAL_TYPES:
            block("INVALID_VISUAL_TYPE", page_id=page_id, reason=f"Invalid visual_type: {visual_type}")

        body_blocks = _list(slide.get("body_blocks"))
        if not body_blocks:
            block("NO_BODY_BLOCKS", page_id=page_id, reason="Slide has no body_blocks.")
        if len(body_blocks) > 6:
            warn("TOO_MANY_BODY_BLOCKS", page_id=page_id, reason=f"Slide has {len(body_blocks)} body blocks.")

        page_allowed_evidence = set(_list(page.get("evidence_ids")))
        union_block_evidence = set()

        for index, body in enumerate(body_blocks, start=1):
            claim_type = body.get("claim_type")
            evidence_ids = set(_list(body.get("evidence_ids")))
            union_block_evidence |= evidence_ids
            text = str(body.get("text") or "")

            if not str(body.get("label") or "").strip():
                warn("MISSING_BLOCK_LABEL", page_id=page_id, reason=f"Body block {index} has no label.")
            if not text.strip():
                block("EMPTY_BODY_TEXT", page_id=page_id, reason=f"Body block {index} is empty.")
            if len(text) > 220:
                warn("OVERLONG_BODY_BLOCK", page_id=page_id, reason=f"Body block {index} is {len(text)} chars.")

            if claim_type not in ALLOWED_CLAIM_TYPES:
                block("INVALID_CLAIM_TYPE", page_id=page_id, reason=f"Body block {index} uses {claim_type}.")
                continue

            invalid = sorted(evidence_ids - set(evidence_index))
            if invalid:
                block(
                    "INVALID_EVIDENCE_ID",
                    page_id=page_id,
                    reason=f"Body block {index} uses unknown evidence IDs: {invalid}",
                )

            off_page = sorted(evidence_ids - page_allowed_evidence)
            if off_page:
                block(
                    "OFF_PAGE_EVIDENCE",
                    page_id=page_id,
                    reason=f"Body block {index} uses evidence not approved by Pagination: {off_page}",
                )

            for evidence_id in evidence_ids:
                entry = evidence_index.get(evidence_id)
                if entry and entry.get("requirement_id") not in set(_list(page.get("rfp_requirement_ids"))):
                    block(
                        "EVIDENCE_REQUIREMENT_MISMATCH",
                        page_id=page_id,
                        reason=f"{evidence_id} belongs to {entry.get('requirement_id')}.",
                    )

            if claim_type in {"REFERENCE_FACT", "REFERENCE_PATTERN"} and not evidence_ids:
                block(
                    "REFERENCE_WITHOUT_EVIDENCE",
                    page_id=page_id,
                    reason=f"Body block {index} is {claim_type} but has no evidence.",
                )

            if claim_type in {"RFP_FACT", "AI_RECOMMENDATION"} and evidence_ids:
                block(
                    "NON_REFERENCE_WITH_EVIDENCE",
                    page_id=page_id,
                    reason=f"Body block {index} is {claim_type} but cites reference evidence.",
                )

            numeric_tokens = _numbers(text)
            if numeric_tokens:
                if claim_type == "RFP_FACT":
                    unsupported = sorted(token for token in numeric_tokens if token not in rfp_blob)
                    if unsupported:
                        block(
                            "UNSUPPORTED_RFP_NUMBER",
                            page_id=page_id,
                            reason=f"RFP_FACT block {index} contains numbers absent from RFP analysis: {unsupported}",
                        )
                elif claim_type in {"REFERENCE_FACT", "REFERENCE_PATTERN"}:
                    evidence_blob = " ".join(
                        _evidence_text(evidence_index[eid])
                        for eid in evidence_ids
                        if eid in evidence_index
                    )
                    unsupported = sorted(token for token in numeric_tokens if token not in evidence_blob)
                    if unsupported:
                        block(
                            "UNSUPPORTED_REFERENCE_NUMBER",
                            page_id=page_id,
                            reason=f"Reference block {index} contains numbers absent from cited evidence: {unsupported}",
                        )
                elif claim_type == "AI_RECOMMENDATION" and not body.get("client_confirmation_required"):
                    block(
                        "UNGROUNDED_RECOMMENDATION_NUMBER",
                        page_id=page_id,
                        reason=(
                            f"AI_RECOMMENDATION block {index} contains numeric values "
                            "without client_confirmation_required=true."
                        ),
                    )

        declared_slide_evidence = set(_list(slide.get("evidence_ids")))
        if declared_slide_evidence != union_block_evidence:
            block(
                "SLIDE_EVIDENCE_SUMMARY_MISMATCH",
                page_id=page_id,
                reason=(
                    f"slide.evidence_ids={sorted(declared_slide_evidence)} but body union="
                    f"{sorted(union_block_evidence)}"
                ),
            )

        if not declared_slide_evidence.issubset(page_allowed_evidence):
            block(
                "SLIDE_OFF_PAGE_EVIDENCE",
                page_id=page_id,
                reason="Slide top-level evidence includes IDs not approved by Pagination.",
            )

    expected_page_ids = set(page_by_id)
    actual_page_ids = set(slide_by_id)
    for page_id in sorted(expected_page_ids - actual_page_ids):
        block("MISSING_SLIDE", page_id=page_id, reason="Pagination page has no slide.")
    for page_id in sorted(actual_page_ids - expected_page_ids):
        block("EXTRA_SLIDE", page_id=page_id, reason="Slide has no matching Pagination page.")

    return {
        "status": "PASS" if not errors else "FAIL",
        "blocking_errors": errors,
        "warnings": warnings,
        "page_count": len(pages),
        "slide_count": len(slides),
        "valid_evidence_ids": sorted(evidence_index),
    }

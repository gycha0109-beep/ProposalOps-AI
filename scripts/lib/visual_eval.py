from __future__ import annotations

import re


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


def validate_visuals(
    visuals_payload: dict,
    slides_payload: dict,
    pagination: dict,
) -> dict:
    visuals = _list(visuals_payload.get("visuals"))
    slides = _list(slides_payload.get("slides"))
    pages = _list(pagination.get("pages"))

    slide_by_id = {slide.get("page_id"): slide for slide in slides if slide.get("page_id")}
    page_by_id = {page.get("page_id"): page for page in pages if page.get("page_id")}

    errors = []
    warnings = []
    seen = set()
    visual_by_id = {}

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

    for visual in visuals:
        page_id = visual.get("page_id")
        if not page_id:
            block("MISSING_PAGE_ID", reason="Visual has no page_id.")
            continue
        if page_id in seen:
            block("DUPLICATE_VISUAL", page_id=page_id, reason="Duplicate visual for page.")
            continue
        seen.add(page_id)
        visual_by_id[page_id] = visual

        slide = slide_by_id.get(page_id)
        page = page_by_id.get(page_id)
        if slide is None or page is None:
            block("UNKNOWN_PAGE_ID", page_id=page_id, reason="Visual has no matching validated slide/page.")
            continue

        visual_type = visual.get("visual_type")
        if visual_type not in ALLOWED_VISUAL_TYPES:
            block("INVALID_VISUAL_TYPE", page_id=page_id, reason=f"Invalid visual_type: {visual_type}")
        if visual_type != slide.get("visual_type"):
            block(
                "VISUAL_TYPE_MISMATCH",
                page_id=page_id,
                reason=f"Slide requires {slide.get('visual_type')}, visual returned {visual_type}.",
            )

        do_not_generate = bool(visual.get("do_not_generate"))
        image_prompt = visual.get("image_prompt")
        if visual_type == "none":
            if not do_not_generate:
                block("NONE_VISUAL_MUST_SKIP", page_id=page_id, reason="visual_type=none requires do_not_generate=true.")
            if image_prompt not in (None, ""):
                block("NONE_VISUAL_HAS_PROMPT", page_id=page_id, reason="visual_type=none must not have image_prompt.")
        elif do_not_generate and image_prompt:
            warn("SKIP_WITH_PROMPT", page_id=page_id, reason="do_not_generate=true but image_prompt is present.")

        data_source = set(_list(visual.get("data_source")))
        slide_evidence = set(_list(slide.get("evidence_ids")))
        if not data_source.issubset(slide_evidence):
            block(
                "VISUAL_OFF_SLIDE_EVIDENCE",
                page_id=page_id,
                reason=f"Visual data_source contains evidence not used by slide: {sorted(data_source - slide_evidence)}",
            )

        diagram = visual.get("diagram_spec") or {}
        nodes = _list(diagram.get("nodes"))
        edges = _list(diagram.get("edges"))
        if visual_type == "process_diagram":
            if len(nodes) < 2 or not edges:
                block(
                    "INVALID_PROCESS_DIAGRAM",
                    page_id=page_id,
                    reason="process_diagram requires at least two nodes and one edge.",
                )

        if visual_type == "data_chart":
            slide_blob = " ".join(
                [
                    str(slide.get("headline") or ""),
                    str(slide.get("subheadline") or ""),
                    " ".join(str(block.get("text") or "") for block in _list(slide.get("body_blocks"))),
                ]
            )
            if not _numbers(slide_blob):
                block(
                    "DATA_CHART_WITHOUT_NUMERIC_INPUT",
                    page_id=page_id,
                    reason="data_chart selected but validated slide contains no numeric data.",
                )

        if visual_type == "reference_image":
            block(
                "REFERENCE_IMAGE_UNAVAILABLE",
                page_id=page_id,
                reason="Phase 4 has no validated reference-image asset channel.",
            )

        visible_diagram_parts = []
        for node in nodes:
            if isinstance(node, dict):
                for key in ("label", "detail", "description", "metric", "text"):
                    if node.get(key) is not None:
                        visible_diagram_parts.append(str(node.get(key)))
        for edge in edges:
            if isinstance(edge, dict) and edge.get("label") is not None:
                visible_diagram_parts.append(str(edge.get("label")))

        prompt_blob = " ".join([
            str(visual.get("purpose") or ""),
            str(visual.get("image_prompt") or ""),
            " ".join(visible_diagram_parts),
        ])
        visual_numbers = _numbers(prompt_blob)
        slide_blob = " ".join(
            [
                str(slide.get("headline") or ""),
                str(slide.get("subheadline") or ""),
                " ".join(str(block.get("text") or "") for block in _list(slide.get("body_blocks"))),
            ]
        )
        slide_numbers = _numbers(slide_blob)
        invented = sorted(visual_numbers - slide_numbers)
        if invented:
            block(
                "VISUAL_INVENTED_NUMBER",
                page_id=page_id,
                reason=f"Visual introduces numeric values not present in validated slide: {invented}",
            )

        if not str(visual.get("purpose") or "").strip() and visual_type != "none":
            warn("MISSING_VISUAL_PURPOSE", page_id=page_id, reason="Generated visual has no purpose.")

    expected = set(slide_by_id)
    actual = set(visual_by_id)
    for page_id in sorted(expected - actual):
        block("MISSING_VISUAL", page_id=page_id, reason="Validated slide has no visual spec.")
    for page_id in sorted(actual - expected):
        block("EXTRA_VISUAL", page_id=page_id, reason="Visual has no matching slide.")

    return {
        "status": "PASS" if not errors else "FAIL",
        "blocking_errors": errors,
        "warnings": warnings,
        "slide_count": len(slides),
        "visual_count": len(visuals),
    }

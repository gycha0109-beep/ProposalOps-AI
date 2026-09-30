from __future__ import annotations


STRATEGY_CHAIN_ERRORS = {
    "UNSUPPORTED_CLAIM",
    "INVALID_REFERENCE",
    "CROSS_PROPOSAL_MERGE",
}
PAGINATION_ERRORS = {
    "MISSING_REQUIREMENT",
    "STRATEGY_PAGE_MISMATCH",
    "DUPLICATE_MESSAGE",
}
SLIDE_ERRORS = {
    "OVERLONG_SLIDE",
}


def route_repairs(issues: list[dict], pagination: dict) -> dict:
    page_by_id = {
        page.get("page_id"): page
        for page in pagination.get("pages", [])
        if page.get("page_id")
    }
    page_ids = set()
    strategy_ids = set()
    scopes = set()
    unroutable = []

    for issue in issues:
        error_type = issue.get("error_type")
        page_id = issue.get("page_id")
        if page_id:
            page_ids.add(page_id)
            page = page_by_id.get(page_id) or {}
            strategy_ids.update(page.get("strategy_ids", []))

        if error_type in STRATEGY_CHAIN_ERRORS:
            scopes.add("strategy_to_visual")
        elif error_type in PAGINATION_ERRORS:
            scopes.add("pagination_to_visual")
        elif error_type in SLIDE_ERRORS:
            scopes.add("slide_visual")
        else:
            unroutable.append(issue)

    if "strategy_to_visual" in scopes:
        scope = "strategy_to_visual"
    elif "pagination_to_visual" in scopes:
        scope = "pagination_to_visual"
    elif "slide_visual" in scopes:
        scope = "slide_visual"
    else:
        scope = None

    escalation_required = bool(unroutable) or not scope or not page_ids
    return {
        "scope": scope,
        "page_ids": sorted(page_ids),
        "strategy_ids": sorted(strategy_ids),
        "unroutable_issues": unroutable,
        "escalation_required": escalation_required,
        "escalation_reason": (
            "QA issues could not be safely mapped to page-scoped repair."
            if escalation_required
            else None
        ),
    }

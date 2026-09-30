# Coverage Validator — Deterministic Gate

Status: **LIVE INTEGRATION VALIDATED**

The production path no longer uses an LLM for structural coverage validation.

Implementation:

- reusable validator: `scripts/lib/pagination_eval.py`
- Dify Phase 3 runner: `scripts/run_dify_phase3_pagination.py`
- Dify Studio code node: `coverage_validator` in `dify/proposalops-phase3-pagination.yml`

Why deterministic code:

- canonical requirement/strategy/evidence IDs are already structured inputs
- missing coverage and invalid references are exact structural checks
- deterministic validation is cheaper, reproducible, and avoids false positives from an LLM judge

## Inputs

1. RFP requirements
2. Pagination Planner output
3. Proposal Strategy
4. Evidence Pack
5. page limit

## BLOCK

- no pages
- page limit exceeded
- duplicate or non-sequential page IDs/numbers
- mandatory requirement missing from every page
- invalid requirement_id
- invalid strategy_id
- invalid evidence_id
- strategy attached to unrelated requirement page
- reference-based strategy without supporting evidence on that page
- evidence attached to the wrong requirement page
- evidence attached to a page with no requirement
- requirement_coverage missing or inconsistent with actual page references

## WARN

- one page contains too many requirements
- duplicate key_message
- fact_risk=high without evidence

## Output

```json
{
  "status": "PASS | FAIL",
  "blocking_errors": [],
  "warnings": [],
  "coverage_summary": {
    "total_requirements": 0,
    "covered": 0,
    "partial": 0,
    "missing": 0
  },
  "requirement_page_map": {}
}
```

## Live result

RFP-TEST-002 / Phase 3:

- pages: 6
- page limit: 8
- requirements: 6
- covered: 6
- missing: 0
- blocking errors: 0
- warnings: 0
- status: PASS

Evidence:

- `reports/dify-phase3-pagination-rfp-test-002.json`
- `reports/dify-phase3-pagination-rfp-test-002.md`

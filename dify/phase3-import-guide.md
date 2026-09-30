# Dify Phase 3 Studio Import Guide

## Artifact

Import:

`dify/proposalops-phase3-pagination.yml`

Target:

- Dify DSL version: 0.7.0
- app mode: workflow
- nodes: 16
- edges: 14
- production Knowledge: ProposalOps Production v1
- page limit: 8

Validate before import:

```bash
python scripts/validate_dify_phase3_dsl.py
```

## Graph

```text
User Input
  ↓
RFP Analyzer
  ↓
Retrieval Planner
  ↓
Parse Dual Queries
  ↓
Retrieve Queries [serial]
  ↓
Merge / Filter Retrieval
  ↓
Evidence Builder
  ↓
Proposal Strategist
  ↓
Pagination Planner
  ↓
Coverage Validator [Code]
  ↓
Pagination + Coverage Output
```

## Workspace bindings

LLM nodes intentionally leave provider/model identifiers unpinned.

After import, confirm these five nodes resolve to the workspace model:

- RFP Analyzer
- Retrieval Planner
- Evidence Builder
- Proposal Strategist
- Pagination Planner

Expected workspace default:

`gpt-5.6-luna`

Knowledge embedding:

`text-embedding-3-small`

Production Knowledge dataset:

`ProposalOps Production v1`

Do not replace it with the benchmark dataset.

## Smoke input

Use:

`data/raw/rfps/RFP-TEST-002.md`

## End outputs

Expected outputs:

- rfp_analysis
- retrieval_plan
- retrieval_trace
- evidence_packs
- proposal_strategy
- pagination
- coverage_validation
- coverage_status

## PASS condition

The Studio smoke test passes when:

1. DSL imports without blocking schema errors.
2. Production Knowledge remains bound.
3. All five LLM nodes resolve to a model.
4. RFP-TEST-002 reaches the End node.
5. coverage_status is PASS.
6. R-201 through R-206 are all covered.
7. No invalid strategy/evidence reference exists.
8. Pagination stays within 8 pages.
9. No benchmark hard-negative asset is used.
10. No unsupported company achievement or quantitative claim is introduced.

Reference live result:

`reports/dify-phase3-pagination-rfp-test-002.json`

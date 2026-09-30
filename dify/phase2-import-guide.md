# Dify Phase 2 Studio Import Guide

## Artifact

Import candidate:

`dify/proposalops-phase2-core.yml`

The file uses JSON syntax that is also valid YAML. This allows zero-dependency structural validation in CI while remaining acceptable to Dify's YAML parser.

Current target:

- Dify App DSL version: **0.7.0**
- app mode: **workflow**
- nodes: **14**
- edges: **12**
- Knowledge dataset: `ProposalOps Production v1`
- dataset id: `21dcb1f3-270f-4991-bcf8-b2782e6cf814`

Validator:

```bash
python scripts/validate_dify_phase2_dsl.py
```

## Why import is manual

The repository secret `DIFY_API_KEY` is a Knowledge Service API credential.

Current Dify App DSL import requires workspace/account authorization with workspace-write and App DSL import/export permission. It is not the same credential class as the Knowledge Service API key.

Therefore the repository automation uploads/searches Knowledge live, but it does not impersonate the user's Studio account to create an App.

## Import

In Dify:

1. Open **Studio**.
2. Choose the option to **Import DSL / Create from DSL**.
3. Upload `dify/proposalops-phase2-core.yml`.
4. If Dify shows a version/dependency warning, review it before confirming.
5. Open the imported workflow.

The workflow deliberately leaves the four LLM node model selectors unpinned so the target workspace uses its configured default reasoning model.

Expected workspace default:

`gpt-5.6-luna`

Expected embedding model for Knowledge:

`text-embedding-3-small`

## Expected node graph

```text
User Input
  ↓
RFP Analyzer
  ↓
Retrieval Planner
  ↓
Parse Dual Queries
  ↓
Retrieve Queries [serial iteration]
  ├─ Parse Query Item
  ├─ Sandbox Rate Limit
  ├─ Production Knowledge
  └─ Pack Retrieval
  ↓
Merge / Filter Retrieval
  ↓
Evidence Builder
  ↓
Proposal Strategist
  ↓
Grounded Strategy Output
```

## Knowledge node check

The **Production Knowledge** node must point to:

`ProposalOps Production v1`

It must not point to the benchmark Knowledge Base.

If the imported node displays a missing dataset warning, reselect the existing production Knowledge Base manually. Do not replace it with the 63-asset benchmark dataset because that dataset contains synthetic hard negatives used only for evaluation.

## Sandbox rate limit

The workflow performs two retrieval queries per RFP requirement.

The iteration is serial and includes a 7-second delay before Knowledge Retrieval so the Sandbox request-rate limit is not exceeded.

Do not switch the query iteration to parallel execution on the Sandbox plan.

## Smoke input

Use the repository fixture:

`data/raw/rfps/RFP-TEST-002.md`

Paste the complete content into `RFP text`.

## Expected final outputs

The End node exposes:

- `rfp_analysis`
- `retrieval_plan`
- `retrieval_trace`
- `evidence_packs`
- `proposal_strategy`

For RFP-TEST-002 the validated API-runner evidence chain selected:

| Requirement | Expected primary evidence |
|---|---|
| R-201 | PA-PR-007-P015 |
| R-202 | PA-PR-007-P016 |
| R-203 | PA-VIDEO-004-P021 |
| R-204 | PA-PR-007-P018 |
| R-205 | PA-CAMP-010-P023 |
| R-206 | PA-CAMP-010-P024 |

The Studio smoke test does not need byte-identical wording, but it must preserve:

- all six requirement IDs
- valid Proposal Asset IDs
- source provenance
- no benchmark distractor IDs
- no unsupported company achievement
- no unsupported numerical claim
- valid requirement → evidence → strategy trace

Reference live result:

`reports/dify-phase2-core-rfp-test-002.json`

## PASS condition

Studio import/smoke is complete when:

1. DSL imports without a blocking schema error.
2. Production Knowledge is bound.
3. All four LLM nodes resolve to the configured workspace model.
4. RFP-TEST-002 runs to the End node.
5. The five expected outputs are present.
6. Evidence IDs reference assets returned by retrieval.
7. No hard-negative benchmark asset is present.
8. Proposal Strategy covers R-201 through R-206.

# Benchmark Scorecard

> Synthetic frozen benchmark. 실제 고객 성과가 아닙니다.

## Fixed live model

- provider: OpenAI Responses API
- model: `gpt-5.6-luna`
- reasoning effort: `low`

## Final candidates

| Track | Frozen candidate | Dev result | Holdout result | Status |
|---|---|---|---|---|
| RFP Analyzer | `v4_compact_grounded` | Assertion 100%, Numeric 100%, Requirement 100%, Schema 100%, Grounding 100% | Assertion 100%, Numeric 100%, Requirement 100%, Schema 100% | **FROZEN / PASS** |
| Proposal Strategist | `v4_explicit_classes` | Requirement 100%, Evidence 100%, Class separation 100%, Unsupported 0 | Requirement 100%, Evidence 100%, Class separation 100%, Unsupported 0 | **FROZEN / PASS** |
| Proposal QA | `v4_compact_taxonomy` | BLOCK 100%, FP 0%, Type 100%, Severity 100% | BLOCK 100%, FP 0%, Type 100%, Severity 100% | **FROZEN / PASS** |

## RFP Analyzer progression

| Version | Assertion | Numeric | Requirement | Schema | Grounding |
|---|---:|---:|---:|---:|---:|
| v0_baseline | 80.83% | 82.86% | 75.00% | 0% | 0% |
| v1_structured | 90.83% | 92.85% | 100% | 100% | 0% |
| v2_grounded | 90.83% | 92.85% | 100% | 0% | 100% |
| v3_final | 90.83% | 82.86% | 100% | 0% | 100% |
| v4_compact_grounded | 100% | 100% | 100% | 100% | 100% |

## E2E validation

- RFP: `RFP-TEST-002`
- final package: **PASS**
- pages: **8**
- slides: **8**
- visuals: **8**
- final QA issues: **0**
- provenance repair cycles: **3**

Evidence:

- `runs/e2e-demo/RFP-TEST-002/final-package-repaired.json`
- `reports/e2e-demo-summary.md`


## Dify live integration

> Synthetic/demo live integration. Frozen prompt benchmark와 구분합니다.

| Phase | Result | Evidence |
|---|---|---|
| Phase 1 Knowledge retrieval | 48 frozen queries complete; DEV Hit@1 90.62%, HOLDOUT Hit@1 93.75%, Hit@3/5 100% | `reports/dify-retrieval-v1-semantic.json` |
| Phase 2 Grounded Strategy Core | PASS; evidence recall/precision/provenance 100%, broken provenance 0 | `reports/dify-phase2-core-rfp-test-002.json` |
| Phase 3 Pagination | PASS; 6/6 requirements covered, 0 blocking errors | `reports/dify-phase3-pagination-rfp-test-002.json` |
| Phase 4 Final Package | PASS; 6 pages/slides/visuals, all deterministic gates PASS, QA issues 0 | `reports/dify-phase4-package-rfp-test-002.json` |

Phase 4 latest successful run used 3 normal-path LLM calls and required 0 repair cycles.
Targeted repair behavior remains evidenced by the legacy E2E and intermediate Phase 4 validation runs.


## Source extraction validation

> Synthetic runtime fixtures. 실제 고객 문서가 아닙니다.

| Adapter | Fixture | Result | LLM calls |
|---|---|---|---:|
| PPTX | 2 slides + speaker notes | PASS | 0 |
| PDF | 2 text pages | PASS | 0 |

Evidence:

- `scripts/extract_proposal_source.py`
- `scripts/validate_extraction_adapter.py`
- `.github/workflows/proposal-source-extraction.yml`
- `docs/proposal-source-extraction.md`

Scanned/image-only PDF OCR는 현재 지원 범위가 아닙니다.

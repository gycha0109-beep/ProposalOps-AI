# RFP Analyzer Candidate Comparison

> Frozen dev benchmark v1 / Gemini 3.6 Flash / evaluator 1.4.

| Version | Assertion | Numeric | Requirement | JSON | Quote Coverage | Quote Validity | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| v0_baseline | 66.66% | 72.86% | 33.33% | 0% | 0% | - | measured |
| v1_structured | 95% | 100% | 100% | 100% | 0% | - | measured |
| v2_grounded | 95% | 100% | 100% | 100% | 100% | 100% | best validated metrics; schema drift observed |
| v3_final | 95% | 90% | 100% | 50% | 50% | 100% | regression: truncation |
| v4_compact_grounded | - | - | - | - | - | - | NOT_EVALUATED — provider unavailable/quota |

## Decision

- v0은 구조화 이전 baseline으로 유지한다.
- v1은 schema 안정성의 기준점이다.
- v2는 현재 dev에서 가장 좋은 정량 결과를 보였지만 `project_overview` / `evaluations` schema drift 때문에 production-safe로 간주하지 않는다.
- v3는 RFP-001에서 JSON truncation이 발생해 production candidate에서 제외한다.
- v4는 v1의 schema + v2 grounding + explicit unknown을 결합한 후보지만, 유효한 모델 출력이 없어 품질 판정을 하지 않는다.
- holdout `RFP-TEST-003`은 아직 열지 않았다.

## Evidence

- `reports/rfp-analyzer-dev-v1-gemini36.json`
- `docs/prompt-failure-analysis/rfp-analyzer-dev-v1.md`
- `reports/rfp-analyzer-v4-acceptance.json`

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

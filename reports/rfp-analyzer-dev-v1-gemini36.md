# RFP Analyzer Benchmark — dev

- benchmark: 1.0
- model: gemini-3.6-flash
- thinking level: medium
- runs: **4**

## Version comparison

| Version | Runs | JSON parseable | Assertion pass | Deliverable | Numeric fidelity | Requirement recall | Unsupported additions |
|---|---:|---:|---:|---:|---:|---:|---:|
| v0_baseline | 1 | 0.00% | 80.00% | 100.00% | 80.00% | 50.00% | 0.00 |
| v1_structured | 1 | 100.00% | 90.00% | 100.00% | 100.00% | 100.00% | 0.00 |
| v2_grounded | 1 | 100.00% | 66.67% | 100.00% | 57.14% | 100.00% | 0.00 |
| v3_final | 1 | 100.00% | 91.67% | 100.00% | 85.71% | 100.00% | 0.00 |

## Interpretation rule

이 보고서는 frozen benchmark의 raw run을 기계적으로 집계한다. synthetic benchmark 결과이며 실제 고객 생산성 개선 수치로 해석하지 않는다.

실패 run은 삭제하지 않고 runs/에 그대로 보존한다.

# RFP Analyzer Benchmark — dev

- benchmark: 1.0
- model: gpt-5.6-luna
- thinking level: low
- runs: **10**

## Version comparison

| Version | Runs | JSON | Schema | Truncated | Assertion | Deliverable | Numeric | Requirement | Quote coverage | Quote validity | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v0_baseline | 2 | 0.00% | 0.00% | 0.00% | 80.83% | 100.00% | 82.86% | 75.00% | 0.00% | - | 0.00 |
| v1_structured | 2 | 100.00% | 100.00% | 0.00% | 90.83% | 100.00% | 92.85% | 100.00% | 0.00% | - | 0.00 |
| v2_grounded | 2 | 100.00% | 0.00% | 0.00% | 90.83% | 100.00% | 92.85% | 100.00% | 100.00% | 100.00% | 0.00 |
| v3_final | 2 | 100.00% | 0.00% | 0.00% | 90.83% | 100.00% | 82.86% | 100.00% | 100.00% | 100.00% | 0.00 |
| v4_compact_grounded | 2 | 100.00% | 100.00% | 0.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00 |

## Interpretation rule

이 보고서는 frozen benchmark의 raw run을 기계적으로 집계한다. synthetic benchmark 결과이며 실제 고객 생산성 개선 수치로 해석하지 않는다.

실패 run은 삭제하지 않고 runs/에 그대로 보존한다.

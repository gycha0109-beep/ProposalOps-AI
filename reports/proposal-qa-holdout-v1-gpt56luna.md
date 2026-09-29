# Proposal QA Benchmark — holdout

- benchmark: `1.0`
- model: `gpt-5.6-luna`
- reasoning effort: `low`
- runs: **5**

| Version | JSON | Coverage | BLOCK recall | WARN recall | All error recall | False positive | Type accuracy | Severity accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v0_baseline | 100.00% | 100.00% | 100.00% | - | 100.00% | 100.00% | 0.00% | 0.00% |
| v1_rules | 100.00% | 100.00% | 100.00% | - | 100.00% | 0.00% | 60.00% | 100.00% |
| v2_evidence | 100.00% | 100.00% | 100.00% | - | 100.00% | 0.00% | 0.00% | 100.00% |
| v3_final | 100.00% | 100.00% | 100.00% | - | 100.00% | 0.00% | 0.00% | 100.00% |
| v4_compact_taxonomy | 100.00% | 100.00% | 100.00% | - | 100.00% | 0.00% | 100.00% | 100.00% |

Synthetic injected-error benchmark. Raw outputs are retained; clean-case false positives are not discarded.

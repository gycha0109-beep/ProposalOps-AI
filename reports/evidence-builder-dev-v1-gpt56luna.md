# Evidence Builder Benchmark — dev

- benchmark: `1.0`
- model: `gpt-5.6-luna`
- runs: **2**

| Version | JSON | PASS | Primary recall | Precision | Reject prohibited | Provenance | Status | Company violations | Numeric violations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v0_baseline | 100.00% | 0.00% | 100.00% | 81.82% | 100.00% | 0.00% | 100.00% | 0.00 | 0.00 |
| v1_grounded | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00 | 0.00 |

The six cases use real Dify semantic top-5 retrieval results from RFP-TEST-002.
Hard-negative assets remain in candidate lists where retrieval returned them.

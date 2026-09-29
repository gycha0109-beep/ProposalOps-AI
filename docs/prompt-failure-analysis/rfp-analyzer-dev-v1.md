# RFP Analyzer Dev Failure Analysis — Benchmark v1

> 모델: Gemini 3.6 Flash / thinking medium. 아래 내용은 frozen dev RFP 2종의 기존 raw output 8건을 evaluator 1.5로 재평가한 결과다.

## Baseline

| Version | Assertion | Numeric | Requirement | JSON | Schema | Quote Coverage | Quote Validity |
|---|---:|---:|---:|---:|---:|---:|---:|
| v0_baseline | 66.66% | 72.86% | 33.33% | 0% | 0% | 0% | - |
| v1_structured | 95% | 100% | 100% | 100% | 100% | 0% | - |
| v2_grounded | 95% | 100% | 100% | 100% | 0% | 100% | 100% |
| v3_final | 95% | 90% | 100% | 50% | 0% | 50% | 100% |

## F-001 — Unstructured baseline

`v0_baseline`은 두 RFP 모두 자유형 응답이어서 JSON parseable rate가 0%였다. 요구사항 관련 assertion recall도 평균 33.33%였다.

Design implication: downstream workflow에서 사용할 RFP Analyzer는 자유형 응답을 허용하지 않는다.

## F-002 — Empty string instead of explicit unknown

`v1_structured / RFP-TEST-001`은 예산이 원문에 없을 때 `budget: ""`를 반환했다.

Design implication: 누락 값 표현을 정확히 `unknown` 하나로 고정한다.

## F-003 — Grounding improves traceability

`v2_grounded`는 source quote coverage 100%, validity 100%를 기록했다. 기존 v1의 정확도를 유지하면서 모든 평가 대상 항목에 실제 RFP 근거를 연결했다.

Design implication: source grounding은 유지한다.

## F-004 — Schema drift

`v2_grounded` raw output에서 고정 계약과 다른 key가 생성됐다.

- `project` → `project_overview`
- `evaluation` → `evaluations`

내용 정확도는 evaluator의 semantic fallback으로 인정할 수 있지만 canonical schema validity는 0%다. 실제 agent pipeline에서는 계약 파손 위험이다.

Design implication: exact top-level schema와 `Do not rename keys` 규칙을 명시한다.

## F-005 — Instruction bloat and truncation

`v3_final / RFP-TEST-001`은 grounding과 fail-closed 규칙을 강화했지만 출력이 장황해져 JSON이 끝까지 닫히지 않았다.

- JSON parseable: FAIL
- output_truncated: true
- v3 전체 JSON parseable rate: 50%

Design implication: submission rules, open questions, coverage summary, interpretation note 등 RFP Analyzer 핵심 추출에 필요하지 않은 출력을 제거한다.

## v4 design decision

`v4_compact_grounded`는 새 규칙을 계속 추가하는 방식이 아니라 다음 세 요소만 결합한다.

1. v1의 고정 schema
2. v2의 source_quote grounding
3. v3의 explicit unknown policy

그리고 schema alias, extra top-level keys, interpretation_note, 장문 source_quote를 금지한다.

## Raw evidence

- `runs/rfp_analyzer/benchmark-v1-gemini36/dev/v1_structured/`
- `runs/rfp_analyzer/benchmark-v1-gemini36/dev/v2_grounded/`
- `runs/rfp_analyzer/benchmark-v1-gemini36/dev/v3_final/`
- `reports/rfp-analyzer-dev-v1-gemini36.json`

## v4 execution status

`v4_compact_grounded`의 prompt와 acceptance criteria는 dev 실행 전에 고정했다.

그러나 유효한 v4 모델 출력은 확보하지 못했다.

- first attempt: RFP-001 / RFP-002 모두 Gemini 503
- bounded retry attempt: provider quota exhausted (429) / availability error
- final provider RetryInfo window attempt: RFP-001 503 after bounded retry, RFP-002 429

따라서 v4 status는 `NOT_EVALUATED`다. 품질 실패로 간주하지 않으며 holdout은 열지 않았다.

Evidence:
- `reports/rfp-analyzer-v4-acceptance.json`
- `runs/rfp_analyzer/benchmark-v1-gemini36/dev/_failures/`

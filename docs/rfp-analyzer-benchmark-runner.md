# RFP Analyzer Benchmark Runner

## Purpose

동일 모델·동일 파라미터·동일 frozen RFP에서 prompt version만 바꿔 결과 차이를 측정합니다.

Config:

`configs/rfp-analyzer-benchmark-v1.json`

## Fixed model condition

- provider: OpenAI Responses API
- model: `gpt-5.6-luna`
- reasoning effort: `low`
- max output tokens: 6000
- sampling parameters: 별도 지정하지 않음
- secret: `OPENAI_API_KEY`

## Frozen split

Dev:

- RFP-TEST-001
- RFP-TEST-002

Holdout:

- RFP-TEST-003

holdout은 candidate가 dev acceptance를 통과해 prompt SHA와 candidate commit이 frozen된 뒤에만 실행 가능합니다.

State:

`evals/frozen/v1/rfp-analyzer-candidate.json`

## Prompt variants

- v0_baseline
- v1_structured
- v2_grounded
- v3_final
- v4_compact_grounded

실험 설명은 모델 입력에 포함하지 않습니다. `## Prompt` 이후 executable body만 전달합니다.

## Dev result

`reports/rfp-analyzer-dev-v1-gpt56luna.json`

| Version | Assertion | Numeric | Requirement | JSON | Schema | Quote grounding |
|---|---:|---:|---:|---:|---:|---:|
| v0 | 80.83% | 82.86% | 75% | 0% | 0% | 0% |
| v1 | 90.83% | 92.85% | 100% | 100% | 100% | 0% |
| v2 | 90.83% | 92.85% | 100% | 100% | 0% | 100% |
| v3 | 90.83% | 82.86% | 100% | 100% | 0% | 100% |
| **v4** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** |

v4 failed assertion: 0.

## Holdout result

`reports/rfp-analyzer-holdout-v1-gpt56luna.json`

Frozen v4 / RFP-TEST-003:

- assertion pass: 100%
- deliverable recall: 100%
- numeric fidelity: 100%
- requirement recall: 100%
- source quote coverage: 100%
- source quote validity: 100%
- canonical schema validity: 100%
- unsupported additions: 0

holdout 결과를 본 뒤 v4 prompt를 수정하지 않습니다.

## Evaluator

`scripts/lib/rfp_eval.py`

Evaluator 1.5는 다음을 측정합니다.

- assertion pass
- deliverable recall
- numeric fidelity
- requirement recall
- unsupported additions
- source quote coverage
- source quote validity
- canonical schema validity
- JSON parseability
- output truncation

v0처럼 자유형 출력인 경우 별도의 LLM normalizer를 사용하지 않습니다.

## Raw evidence

각 call은 다음을 저장합니다.

- prompt file / SHA-256
- model / reasoning effort
- RFP source / frozen gold
- response ID
- token usage
- raw output
- parsed output
- evaluator result
- git commit

Root:

`runs/rfp_analyzer/benchmark-v1-gpt56luna/`

## Production promotion

Dev acceptance:

`reports/rfp-analyzer-v4-acceptance.json`

Frozen state:

`evals/frozen/v1/rfp-analyzer-candidate.json`

Production:

`prompts/production/rfp_analyzer.md`

Status: **FROZEN**

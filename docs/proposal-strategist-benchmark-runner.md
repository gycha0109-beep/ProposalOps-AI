# Proposal Strategist Benchmark Runner

## Purpose

Proposal Strategist prompt variants를 frozen RFP + neutral Evidence Pack에서 비교합니다.

## Frozen set

Dev:

- RFP-TEST-001
- RFP-TEST-002

Holdout:

- RFP-TEST-003

Gold:

`evals/frozen/v1/{dev,holdout}/strategist/`

Neutral evidence input:

`evals/strategist/inputs-v1.json`

51개 normal Proposal Asset에서 frozen gold가 허용한 asset ID를 실제로 materialize했습니다.

- missing allowed assets: 0
- forbidden-claim leakage: 0

## Fixed model condition

- provider: OpenAI Responses API
- model: `gpt-5.6-luna`
- reasoning effort: `low`

## Batch execution

dev RFP 2개를 prompt version당 한 batch로 처리합니다.

## Metrics

- result coverage
- requirement coverage
- evidence citation coverage
- evidence validity
- unsupported company claim count
- unsupported quantitative claim count
- information class separation
- invalid evidence reference count
- JSON parseability

Evaluator:

`scripts/lib/strategy_eval.py`

## Prompt progression

v3:

- requirement coverage: 100%
- evidence citation/validity: 100%
- unsupported claims: 0
- information class separation: 50%

문제는 한 RFP에서 모든 전략을 REFERENCE_PATTERN으로만 분류하면서 AI_RECOMMENDATION을 명시적으로 분리하지 않은 것이었습니다.

v4 `v4_explicit_classes`는 다음 4개 class를 output contract에 고정합니다.

- RFP_FACT
- REFERENCE_FACT
- REFERENCE_PATTERN
- AI_RECOMMENDATION

## v4 dev result

`reports/proposal-strategist-dev-v1-gpt56luna.json`

- result coverage: 100%
- requirement coverage: 100%
- evidence citation coverage: 100%
- evidence validity: 100%
- information class separation: 100%
- unsupported company claims: 0
- unsupported quantitative claims: 0
- invalid evidence references: 0

Acceptance:

`reports/proposal-strategist-v4-acceptance.json`

## v4 holdout result

`reports/proposal-strategist-holdout-v1-gpt56luna.json`

동일 핵심 metric 모두 100%, unsupported claim / invalid evidence reference 모두 0입니다.

## Candidate freeze

`evals/frozen/v1/proposal-strategist-candidate.json`

Production:

`prompts/production/proposal_strategist.md`

Status: **FROZEN**

## E2E use

frozen v4 RFP-TEST-002 strategy output을 E2E demo의 upstream source로 재사용했습니다.

최종 provenance-chain repair에서는 ST-05 / ST-06만 evidence 범위에 맞게 수정했고, affected downstream pages만 함께 repair했습니다.

Evidence:

`runs/e2e-demo/RFP-TEST-002/repair-cycle-3.json`

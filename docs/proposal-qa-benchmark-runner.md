# Proposal QA Benchmark Runner

## Purpose

Proposal QA prompt variants를 frozen injected-error benchmark에서 비교합니다.

## Frozen QA set

- total cases: 20
- dev: 14
- holdout: 6
- gold labels: `evals/qa-injected-errors/cases.json`
- neutral model inputs: `evals/qa-injected-errors/inputs-v1.json`

neutral input에는 gold `type / severity / reason`을 넣지 않습니다.

## Fixed model condition

- provider: OpenAI Responses API
- model: `gpt-5.6-luna`
- reasoning effort: `low`
- secret: `OPENAI_API_KEY`

## Batch execution

case별로 API를 호출하지 않고 split 전체를 prompt version당 한 batch로 처리합니다.

Dev 14 cases × version당 1 call.

## Prompt progression

v3는 오류 탐지 자체는 수행했지만 executable prompt에 explicit taxonomy enum이 빠져 error type accuracy가 0%였습니다.

v4 `v4_compact_taxonomy`에서 허용 type을 명시적으로 고정했습니다.

- MISSING_REQUIREMENT
- UNSUPPORTED_CLAIM
- INVALID_REFERENCE
- CROSS_PROPOSAL_MERGE
- STRATEGY_PAGE_MISMATCH
- DUPLICATE_MESSAGE
- OVERLONG_SLIDE

Severity:

- BLOCK
- WARN
- INFO

## Metrics

- result coverage
- BLOCK detection recall
- WARN detection recall
- all-error recall
- clean-case false-positive rate
- error-type accuracy
- severity accuracy
- JSON parseability

Evaluator:

`scripts/lib/qa_eval.py`

## v4 dev result

`reports/proposal-qa-dev-v1-gpt56luna.json`

- result coverage: 100%
- BLOCK recall: 100%
- WARN recall: 100%
- false positive: 0%
- error type accuracy: 100%
- severity accuracy: 100%

Acceptance:

`reports/proposal-qa-v4-acceptance.json`

## v4 holdout result

`reports/proposal-qa-holdout-v1-gpt56luna.json`

- BLOCK recall: 100%
- false positive: 0%
- error type accuracy: 100%
- severity accuracy: 100%

첫 holdout workflow에서 이전 variants도 같이 실행된 기록은 삭제하지 않고 보존합니다. frozen v4는 holdout 결과를 본 뒤 수정하지 않습니다.

## Candidate freeze

`evals/frozen/v1/proposal-qa-candidate.json`

Status:

- candidate: `v4_compact_taxonomy`
- frozen: true
- holdout allowed: true

Production:

`prompts/production/proposal_qa.md`

Status: **FROZEN**

## E2E use

동일 frozen QA prompt를 최종 proposal package 검증에도 사용했습니다.

최종 E2E re-QA:

`runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-3.json`

Result:

`PASS / issues=[]`

# Proposal QA Benchmark Runner

## Purpose

Proposal QA prompt variants를 frozen injected-error benchmark에서 동일 조건으로 비교합니다.

## Frozen QA set

- total cases: 20
- dev: 14
- holdout: 6
- gold labels: `evals/qa-injected-errors/cases.json`
- neutral model inputs: `evals/qa-injected-errors/inputs-v1.json`

`inputs-v1.json`에는 gold `type / severity / reason`을 넣지 않습니다. RFP 요구사항, company_facts, evidence catalog, draft fragment만 제공합니다.

## Batch execution

dev에서는 case마다 모델을 따로 호출하지 않습니다.

```text
14 dev cases
×
4 prompt versions
=
4 Gemini calls
```

각 prompt version은 dev 14건을 한 batch로 받아 14개 결과를 JSON 배열로 반환합니다.

## Metrics

- result coverage
- BLOCK detection recall
- WARN detection recall
- all-error detection recall
- clean-case false-positive rate
- error-type accuracy
- severity accuracy
- JSON parseable rate

## Acceptance candidate

현재 사전 고정 candidate는 `v3_final`입니다.

Dev acceptance:
- JSON 100%
- result coverage 100%
- BLOCK recall >= 90%
- WARN recall = 100%
- false positive = 0%
- type accuracy >= 80%
- severity accuracy >= 90%

기준 파일: `evals/acceptance/proposal-qa-v3-dev.json`

## Holdout protection

`evals/frozen/v1/proposal-qa-candidate.json`가 `frozen`이며 `holdout_allowed=true`가 되기 전에는 holdout 실행이 차단됩니다.

## Live execution status

Runner/workflow는 준비됐지만 아직 Gemini live QA run은 수행하지 않았습니다.

- workflow: `.github/workflows/proposal-qa-live.yml`
- runner: `scripts/run_qa_benchmark.py`
- aggregator: `scripts/aggregate_qa_runs.py`
- evaluator: `scripts/lib/qa_eval.py`

현재 free-tier quota를 RFP Analyzer 실험에서 소진했기 때문에 QA live 호출은 보류합니다.

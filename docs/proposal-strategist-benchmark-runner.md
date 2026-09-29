# Proposal Strategist Benchmark Runner

## Purpose

Proposal Strategist prompt variants를 frozen RFP/evidence benchmark에서 동일 조건으로 비교합니다.

## Frozen set

- dev RFP: `RFP-TEST-001`, `RFP-TEST-002`
- holdout RFP: `RFP-TEST-003`
- gold: `evals/frozen/v1/{dev,holdout}/strategist/`
- neutral evidence inputs: `evals/strategist/inputs-v1.json`

neutral input은 51개 정상 Proposal Asset에서 gold가 허용한 asset ID를 실제로 찾아 materialize했습니다.

- missing allowed asset: 0
- forbidden claim leakage: 0

## Batch execution

dev 2개 RFP를 prompt version당 한 batch로 처리합니다.

```text
2 dev RFP
×
4 prompt versions
=
4 GPT-5.6 Luna calls
```

## Metrics

- result coverage
- requirement coverage
- evidence citation coverage
- evidence validity
- unsupported company claim count
- unsupported quantitative claim count
- information class separation
- invalid evidence reference count
- JSON parseable rate

## Dev acceptance

v3는 grounding을 통과했지만 information-class separation이 50%여서 v4 candidate로 교정했습니다.

- JSON = 100%
- result coverage = 100%
- requirement coverage >= 95%
- evidence citation coverage >= 90%
- evidence validity >= 90%
- unsupported company claim = 0
- unsupported quantitative claim = 0
- information class separation = 100%
- invalid evidence reference = 0

기준 파일: `evals/acceptance/proposal-strategist-v3-dev.json`

## Holdout

`evals/frozen/v1/proposal-strategist-candidate.json`가 frozen 상태가 되기 전까지 RFP-TEST-003 실행은 차단됩니다.

## Current status

Runner/evaluator/aggregator/workflow와 CI plan validation까지 완료됐습니다.

아직 Strategist live GPT-5.6 Luna run은 수행하지 않았습니다.

- runner: `scripts/run_strategy_benchmark.py`
- evaluator: `scripts/lib/strategy_eval.py`
- aggregator: `scripts/aggregate_strategy_runs.py`
- workflow: `.github/workflows/proposal-strategist-live.yml`

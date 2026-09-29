# RFP Analyzer Benchmark Runner

## Purpose

동일 모델·동일 파라미터·동일 RFP에서 prompt version만 바꿔 결과 차이를 측정합니다.

현재 benchmark config:

`configs/rfp-analyzer-benchmark-v1.json`

## Fixed model condition

현재 live benchmark candidate는:

- provider: OpenAI Responses API
- model: `gpt-6-sol`
- reasoning effort: `medium`
- max output tokens: `6000`
- temperature: 사용하지 않음

Reasoning 모델에서 reasoning effort를 사용하는 비교이므로 temperature를 섞지 않습니다.

공식 문서:
- https://developers.openai.com/api/docs/guides/reasoning
- https://developers.openai.com/api/reference/responses/create

## Dev matrix

기본 설정:

```text
2 RFP
× 4 prompt versions
× 3 repeats
= 24 live model calls
```

실행:

```bash
OPENAI_API_KEY=... python scripts/run_rfp_benchmark.py \
  --split dev \
  --versions all \
  --repetitions 3
```

API 호출 없이 실행 계획만 검증:

```bash
python scripts/run_rfp_benchmark.py \
  --split dev \
  --versions all \
  --repetitions 3 \
  --plan-only
```

## Prompt isolation

실험 설명은 모델 입력에 포함하지 않습니다.

각 prompt 파일에서:
- `## Prompt`, 또는
- `## Role`

이후의 실행 본문만 모델 instructions로 전달합니다.

따라서 "v2는 grounding을 추가했다"와 같은 메타 설명이 결과에 힌트를 주지 않습니다.

## v0 evaluation

v0는 자유형 응답을 허용합니다.

별도의 LLM normalizer를 두지 않습니다. 두 번째 모델이 누락 내용을 보완해 benchmark를 오염시킬 수 있기 때문입니다.

Evaluator는:
- JSON이면 구조적으로 평가
- JSON이 아니면 raw text에서 직접 검증 가능한 assertion만 평가
- 구조가 필요한 `evaluation_sum` 등은 안전하게 평가할 수 없으면 실패 처리

합니다.

## Raw evidence

각 live call은 다음을 저장합니다.

- prompt version
- prompt SHA-256
- model
- reasoning effort
- max output tokens
- RFP source path
- gold path
- provider response ID
- token usage
- raw output
- parsed JSON when available
- evaluator result
- git commit

위치:

`runs/rfp_analyzer/benchmark-v1/`

## Holdout protection

holdout은 기본 실행이 거부됩니다.

직접 실행:

```bash
python scripts/run_rfp_benchmark.py \
  --split holdout \
  --versions all \
  --repetitions 1 \
  --confirm-holdout
```

GitHub Actions에서도 `confirm_holdout=true`를 명시해야 합니다.

holdout 결과를 본 뒤 같은 benchmark v1에 맞춰 prompt를 다시 튜닝하지 않습니다.

## Aggregation

```bash
python scripts/aggregate_rfp_runs.py \
  --root runs/rfp_analyzer/benchmark-v1/dev \
  --json-out reports/rfp-analyzer-dev-v1.json \
  --md-out reports/rfp-analyzer-dev-v1.md
```

집계 지표:

- JSON parseable rate
- assertion pass rate
- deliverable recall
- numeric fidelity
- requirement assertion recall
- unsupported addition count
- repeated-run standard deviation
- token usage

## Prompt Diff

```bash
python scripts/generate_prompt_diff.py \
  --from-version v0_baseline \
  --to-version v3_final \
  --out reports/rfp-analyzer-v0-v3.diff
```

## GitHub Actions

`.github/workflows/rfp-analyzer-live.yml`

수동 workflow만 live model을 호출합니다.

필요 Repository Secret:

`OPENAI_API_KEY`

workflow 완료 시 raw run과 report를 Git에 커밋합니다.

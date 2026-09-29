# RFP Analyzer Benchmark Runner

## Purpose

동일 모델·동일 파라미터·동일 RFP에서 prompt version만 바꿔 결과 차이를 측정합니다.

현재 benchmark config:

`configs/rfp-analyzer-benchmark-v1.json`

## Fixed model condition

현재 live benchmark 조건:

- provider: Gemini Developer API / GenerateContent
- model: `gemini-3.8-flash`
- thinking level: `medium`
- max output tokens: `6000`
- sampling parameters: 별도 지정하지 않음
- request delay: 4초

Gemini 3.8 Flash는 현재 GA Flash 모델이며 `low / medium / high` thinking level을 지원합니다.

## Dev matrix

무료 RPD를 소모하지 않도록 현재 dev 반복 횟수를 2회로 고정합니다.

```text
2 RFP
× 4 prompt versions
× 2 repeats
= 16 live model calls
```

실행:

```bash
GEMINI_API_KEY=... python scripts/run_rfp_benchmark.py \
  --split dev \
  --versions all \
  --repetitions 2
```

API 호출 없이 실행 계획만 검증:

```bash
python scripts/run_rfp_benchmark.py \
  --split dev \
  --versions all \
  --repetitions 2 \
  --plan-only
```

## Prompt isolation

실험 설명은 모델 입력에 포함하지 않습니다.

각 prompt 파일에서 `## Prompt` 또는 `## Role` 이후의 실행 본문만 Gemini system instruction으로 전달합니다.

따라서 "v2는 grounding을 추가했다" 같은 메타 설명은 모델이 보지 않습니다.

## v0 evaluation

v0는 자유형 응답을 허용합니다.

별도의 LLM normalizer를 두지 않습니다. 두 번째 모델이 누락 내용을 보완해 benchmark를 오염시킬 수 있기 때문입니다.

Evaluator는 JSON이면 구조적으로 평가하고, 자유형이면 raw text에서 직접 검증 가능한 assertion만 평가합니다.

## Raw evidence

각 live call에는 다음을 저장합니다.

- prompt version / SHA-256
- Gemini model version
- thinking level
- max output tokens
- RFP source / gold path
- token usage / thoughts token count
- raw output
- parsed JSON when available
- evaluator result
- git commit

위치:

`runs/rfp_analyzer/benchmark-v1/`

## Failure policy

Gemini 429/503에 자동 재시도하지 않습니다. 무료 RPD를 불필요하게 소모할 수 있기 때문입니다.

오류가 발생하면:
1. 실패 정보를 `_failures/`에 기록
2. 즉시 실행 중단
3. 완료된 raw run과 실패 evidence를 Git에 보존

하도록 구성했습니다.

## Holdout protection

holdout은 기본 실행이 거부됩니다.

```bash
python scripts/run_rfp_benchmark.py \
  --split holdout \
  --versions all \
  --repetitions 1 \
  --confirm-holdout
```

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
- input / output / reasoning token usage

## GitHub Actions

`.github/workflows/rfp-analyzer-live.yml`

필요 Repository Secret:

`GEMINI_API_KEY`

workflow 완료 시 raw run과 report를 Git에 커밋합니다.

# Dify Knowledge Phase 1

## Goal

ProposalOps AI의 Proposal Asset을 Dify Knowledge에 실제로 넣을 수 있는 형태로 준비하고, 기존 frozen retrieval benchmark와 같은 조건에서 검색 품질을 비교한다.

> 모든 데이터는 synthetic/demo이다.

## Corpus split

### Production Knowledge

경로:

`exports/dify/knowledge-v1/`

구성:

- normal Proposal Asset: **51**
- hard negatives: **0**
- intended use: 실제 workflow Retrieval Planner / Evidence Builder

### Retrieval Benchmark Knowledge

경로:

`exports/dify/benchmark-v1/`

구성:

- normal Proposal Asset: **51**
- hard negatives: **12**
- total: **63**
- intended use: lexical baseline과 like-for-like retrieval 비교

Production Knowledge와 benchmark corpus를 분리한 이유는 hard negative를 실제 제안서 지식으로 사용하지 않기 위해서다.

## Document strategy

Dify에는 **1 Proposal Asset = 1 document**로 넣는다.

Document name:

```text
{asset_id}__{title}
```

예:

```text
PA-CAMP-010-P023__운영정보 변경 검수 및 갱신
```

Document body에는 다음 provenance를 항상 포함한다.

- asset_id
- proposal_id
- category
- client_type
- project_type
- page / page_type / section
- reuse_level
- sensitivity
- source file/page/type
- tags

즉 native metadata가 꺼져도 retrieval result의 document name/content만으로 asset provenance를 복구할 수 있다.

## Native metadata

Schema:

`exports/dify/knowledge-v1/metadata-schema.json`

Fields:

- asset_id
- proposal_id
- category
- client_type
- project_type
- page
- page_type
- section
- reuse_level
- sensitivity
- source_file
- source_page
- source_type
- tags

업로더는 Dify metadata API가 사용 가능한 경우 field 생성 후 document metadata를 동기화한다.

metadata 기능을 사용하지 않으려면:

```bash
python scripts/upload_dify_knowledge.py --skip-native-metadata
```

## Export regeneration

Production:

```bash
python scripts/export_dify_knowledge.py \
  --out exports/dify/knowledge-v1

python scripts/validate_dify_export.py \
  --root exports/dify/knowledge-v1 \
  --expected-count 51
```

Benchmark:

```bash
python scripts/export_dify_knowledge.py \
  --out exports/dify/benchmark-v1 \
  --include-distractors

python scripts/validate_dify_export.py \
  --root exports/dify/benchmark-v1 \
  --expected-count 63 \
  --allow-distractors
```

## Required Dify secrets

실제 Dify API를 호출할 때 필수인 값은 하나다.

```text
DIFY_API_KEY
```

workflow가 다음 Knowledge Base를 이름으로 조회하고, 없으면 자동 생성한다.

- `ProposalOps Production v1`
- `ProposalOps Benchmark v1`

생성된 ID는 `runs/dify/datasets.json`에 저장된다.

Optional override:

```text
DIFY_DATASET_ID
DIFY_BENCHMARK_DATASET_ID
DIFY_API_BASE
```

기존 dataset을 강제로 사용하고 싶을 때만 ID override를 등록한다.

기본값:

```text
https://api.dify.ai/v1
```

## One-command Phase 1

GitHub Actions의 `Dify Knowledge Phase 1` workflow에서 operation을 `full-phase1`으로 실행하면:

```text
DIFY_API_KEY
→ dataset 2개 자동 생성/재사용
→ production 51개 업로드
→ benchmark 63개 업로드
→ frozen retrieval query 48개 실행
→ reports/dify-retrieval-v1.json 저장
```

으로 이어진다.

## Upload plan

Production:

```bash
python scripts/upload_dify_knowledge.py \
  --manifest exports/dify/knowledge-v1/documents.jsonl \
  --metadata-schema exports/dify/knowledge-v1/metadata-schema.json
```

Benchmark:

```bash
python scripts/upload_dify_knowledge.py \
  --manifest exports/dify/benchmark-v1/documents.jsonl \
  --metadata-schema exports/dify/benchmark-v1/metadata-schema.json \
  --dataset-id "$DIFY_BENCHMARK_DATASET_ID"
```

업로더 동작:

1. 기존 document name 조회
2. 같은 document는 skip
3. `POST /datasets/{dataset_id}/document/create-by-text`
4. native metadata field 생성
5. `POST /datasets/{dataset_id}/documents/metadata`
6. asset_id ↔ Dify document_id state 저장

State:

`runs/dify/knowledge-v1/upload-state.json`

## Rate limit

업로더는 모든 Dify Knowledge API 요청 사이에 기본 **7초** 간격을 둔다.

환경/요금제에 따라:

```bash
--delay-seconds N
```

으로 조정할 수 있다.

## Retrieval benchmark

Runner:

`scripts/evaluate_dify_retrieval.py`

Frozen cases:

- dev: 32
- holdout: 16
- total retrieval calls: 48

실행:

```bash
python scripts/evaluate_dify_retrieval.py \
  --dataset-id "$DIFY_BENCHMARK_DATASET_ID" \
  --search-method semantic_search \
  --top-k 5
```

결과:

`reports/dify-retrieval-v1.json`

Metrics:

- Hit@1
- Hit@3
- Hit@5
- MRR
- top-1 miss cases

비교 대상:

`evals/baselines/retrieval-v1.json`

Local lexical baseline:

| Split | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| dev | 90.62% | 100% | 100% | 0.9531 |
| holdout | 93.75% | 100% | 100% | 0.9688 |

Dify benchmark dataset 역시 동일한 **51 normal + 12 hard negative = 63** corpus를 사용해야 직접 비교한다.

## Live Sandbox result — 2026-09-30

실제 Dify Cloud Sandbox Service API 연결을 완료했다.

### Upload

무료 플랜의 50-document 제한 때문에 원본 export의 **1 Asset = 1 Document** 구조는 보존하되,
Cloud Sandbox 실행에서는 custom separator를 사용해 다음처럼 packing한다.

- Production: **1 Dify document / 51 asset segments**
- Benchmark: **1 Dify document / 63 asset segments**
- 각 segment는 embedded provenance와 `asset_id`를 유지한다.
- Production/Benchmark upload validation: **PASS**
- 63 benchmark segment에 12 hard negatives가 포함된 것을 확인했다.

### Semantic retrieval attempt

High Quality + `semantic_search` 실험은 실제 retrieval이 동작했고 DEV의 첫 20 query까지 결과를 반환했다.

그 뒤 Dify hosted OpenAI quota가 소진되어 다음 오류로 중단됐다.

```text
Model provider langgenius/openai/openai quota exceeded.
```

따라서 이 partial run은 완성된 benchmark score로 사용하지 않는다.

### Provider-free diagnostics

Sandbox에서 추가 결제 없이 끝까지 실행 가능한 경로도 검증했다.

`full_text_search`는 48 query를 완주했지만 score가 0인 동일 상위 결과를 반복해
유효한 retrieval candidate로 채택하지 않았다.

Economy indexing + `keyword_search`는 48 query 전체를 완주했다.

| Split | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| DEV 32 | 12.50% | 15.62% | 15.62% | 0.1406 |
| HOLDOUT 16 | 6.25% | 6.25% | 6.25% | 0.0625 |

Report:

```text
reports/dify-retrieval-v1-economy.json
```

비교 대상 local char n-gram TF-IDF baseline:

| Split | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| DEV 32 | 90.62% | 100% | 100% | 0.9531 |
| HOLDOUT 16 | 93.75% | 100% | 100% | 0.9688 |

Economy 결과는 production candidate가 아니다. 한국어 paraphrase benchmark에 대해 Dify keyword path가
local char n-gram baseline보다 현저히 낮다는 diagnostic evidence로 보존한다.

### Final semantic benchmark

Dify workspace에 사용자 OpenAI Model Provider와 `text-embedding-3-small`을 연결한 뒤
기존 High Quality benchmark dataset에서 `semantic_search` 48-query 전체를 재실행했다.

Report:

```text
reports/dify-retrieval-v1-semantic.json
```

결과:

| Split | Dify Semantic Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| DEV 32 | 90.62% | 100% | 100% | 0.9531 |
| HOLDOUT 16 | 93.75% | 100% | 100% | 0.9688 |

Local char n-gram TF-IDF baseline과 aggregate metric이 정확히 동일하다.

| Split | Local Baseline Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| DEV 32 | 90.62% | 100% | 100% | 0.9531 |
| HOLDOUT 16 | 93.75% | 100% | 100% | 0.9688 |

Semantic top-1 miss:

- DEV `RET-D06`: `PA-DIST-P011`이 top-1, expected `PA-VIDEO-004-P022`는 rank 2
- DEV `RET-D25`: `PA-EDU-006-P010`이 top-1, expected `PA-EDU-006-P011`은 rank 2
- DEV `RET-D31`: `PA-DIST-P005`가 top-1, expected `PA-CAMP-010-P023`은 rank 2
- HOLDOUT `RET-H15`: `PA-EVENT-004-P012`가 top-1, expected `PA-EVENT-004-P013`은 rank 2

모든 miss에서도 정답 asset은 top-2 안에 있었고, 따라서 Hit@3/Hit@5는 DEV/HOLDOUT 모두 100%다.

### Decision

Dify High Quality semantic retrieval은 **유효한 production candidate**다.
다만 현재 frozen corpus에서는 local char n-gram TF-IDF baseline을 aggregate metric 기준으로 능가하지는 않았다.

따라서 Phase 1 결론은:

- Dify integration / Knowledge workflow 검증: **PASS**
- Dify semantic retrieval quality: **PASS**
- local baseline 대비 검색 품질 우위: **동률**
- Economy keyword retrieval: production candidate에서 제외
- 다음 단계에서는 retrieval 자체보다 Evidence Builder / workflow orchestration 연결을 우선한다.

## Current status

완료:

- [x] 51 normal asset production export
- [x] 63 asset fair benchmark export
- [x] provenance embedded document format
- [x] native metadata schema
- [x] Dify create-by-text uploader
- [x] Dify retrieval benchmark runner
- [x] local/CI export integrity validation
- [x] Dify Service API authentication
- [x] Production/benchmark dataset bootstrap
- [x] Sandbox document packing
- [x] Production 51 asset segment upload
- [x] Benchmark 63 asset segment upload
- [x] 48-query Economy/keyword diagnostic benchmark
- [x] Dify workspace own OpenAI provider 연결
- [x] High Quality semantic 48-query benchmark 완주
- [x] semantic miss 분석
- [x] 최종 semantic retrieval report 저장
- [x] live evidence committed to repository

Phase 1: **COMPLETE**

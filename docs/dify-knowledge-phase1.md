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

실제 Dify API를 호출할 때만 필요하다.

Production dataset:

```text
DIFY_API_KEY
DIFY_DATASET_ID
```

Fair retrieval benchmark dataset:

```text
DIFY_API_KEY
DIFY_BENCHMARK_DATASET_ID
```

Optional:

```text
DIFY_API_BASE
```

기본값:

```text
https://api.dify.ai/v1
```

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

## Current status

완료:

- [x] 51 normal asset production export
- [x] 63 asset fair benchmark export
- [x] provenance embedded document format
- [x] native metadata schema
- [x] Dify create-by-text uploader
- [x] Dify native metadata sync
- [x] Dify retrieval benchmark runner
- [x] local/CI export integrity validation

Dify workspace가 있어야 가능한 항목:

- [ ] Production dataset 실제 업로드
- [ ] Benchmark dataset 실제 업로드
- [ ] 48 frozen query live retrieval
- [ ] lexical baseline vs Dify report 확정

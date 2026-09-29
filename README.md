# ProposalOps AI

공공기관 RFP와 과거 제안서 자산을 이용해 **제안 전략 → 목차 → 장표별 텍스트 초안 → 이미지 생성 프롬프트**까지 만드는 AI 제안 자동화 PoC입니다.

이 저장소의 핵심 목적은 단순한 생성 데모가 아니라, **프롬프트 엔지니어링이 동일한 입력에서 결과 품질을 실제로 개선하는지 재현 가능하게 검증하는 것**입니다.

> 모든 제안서/RFP 데이터는 synthetic/demo 데이터입니다. 실제 고객 프로젝트 수행 실적이나 생산성 개선 수치로 표현하지 않습니다.

## What This Project Proves

### 1. Proposal Automation

```text
RFP
 ↓
RFP Analyzer
 ↓
Proposal Asset Retrieval
 ↓
Evidence Validation
 ↓
Proposal Strategist
 ↓
Pagination
 ↓
Slide Draft
 ↓
Image Prompt
 ↓
Proposal QA
```

### 2. Prompt Engineering

세 개의 핵심 prompt track을 동일 frozen benchmark에서 비교합니다.

| Track | 검증할 개선 |
|---|---|
| RFP Analyzer | 요구사항 누락·수치 오류·임의 추정 감소 |
| Proposal Strategist | 근거 반영·요구사항 연결·허위 실적 억제 |
| Proposal QA | 허위 주장·누락·잘못된 reference 탐지 |

각 track은 과거 이력을 꾸민 버전이 아니라 **비교 실험을 위해 사전 정의한 variants**입니다.

```text
v0 Baseline
   ↓
v1 Structured / Rule-based
   ↓
v2 Grounded / Evidence-bound
   ↓
v3 Final candidate
```

## Evaluation Integrity

```text
Synthetic data
      ↓
Gold assertions 작성
      ↓
Benchmark v1 freeze
      ↓
Baseline / variants 실행
      ↓
동일 evaluator로 비교
      ↓
Raw output + metrics 보존
```

Benchmark v1은 현재 **frozen** 상태입니다. 같은 v1 gold file은 결과를 본 뒤 수정하지 않으며, 수정이 필요하면 새 benchmark version을 만듭니다.

- dev RFP: `RFP-TEST-001`, `RFP-TEST-002`
- holdout RFP: `RFP-TEST-003`
- benchmark manifest: `evals/frozen/v1/manifest.json`

아직 frontier-model prompt variants의 **live 비교 run**은 수행하지 않았으므로 Prompt Engineering 개선율은 현재 주장하지 않습니다. RFP Analyzer용 실행·기록·평가·집계 인프라는 완료됐습니다.

## Frozen Benchmark v1

- synthetic proposals: **12**
- normal proposal assets: **51**
- retrieval hard negatives: **12**
- total retrieval assets: **63**
- synthetic RFPs: **3**
- retrieval queries: **48**
  - dev: 32
  - holdout: 16
- injected QA cases: **20**
- prompt experiment tracks: **3**
- prompt variants: **12**

## Retrieval Baseline v1

문자 n-gram TF-IDF lexical baseline을 GitHub Actions에서 실행했습니다.

| Split | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| dev (32) | 90.62% | 100% | 100% | 0.9531 |
| holdout (16) | 93.75% | 100% | 100% | 0.9688 |

hard-negative를 넣기 전에는 Hit@1이 100%였기 때문에 benchmark가 지나치게 쉬운 것으로 판단했고, 의미가 비슷하지만 목적이 다른 distractor를 추가했습니다.

현재 1위 실패 사례도 보존합니다.

- `RET-D06`: 정책 문서 검수 distractor가 영상 게시 전 정책정보 검수보다 위에 랭크
- `RET-D25`: 일반 참여 퍼널이 교육용 마이크로러닝보다 위에 랭크
- `RET-D30`: 정책 사실확인 distractor가 촬영 사용동의 자산보다 위에 랭크
- `RET-H15`: 행사 목적 페이지가 실제 방문 동선 설계 페이지보다 위에 랭크

상세: `docs/retrieval-baseline.md`

> 이 값은 Dify Knowledge 또는 frontier embedding/reranker 성능이 아니라 로컬 lexical baseline입니다.

## Repository Structure

```text
ProposalOps-AI/
├─ .github/workflows/
│  ├─ benchmark-validation.yml\n│  └─ rfp-analyzer-live.yml
├─ docs/
│  ├─ architecture.md
│  ├─ evaluation-methodology.md
│  ├─ prompt-engineering-case-study.md
│  └─ retrieval-baseline.md
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ taxonomy/
├─ prompts/
│  ├─ rfp_analyzer/
│  ├─ proposal_strategist/
│  ├─ proposal_qa/
│  ├─ production/
│  └─ experiment-manifest.json
├─ evals/
│  ├─ frozen/v1/
│  │  ├─ dev/
│  │  └─ holdout/
│  ├─ baselines/
│  └─ qa-injected-errors/
├─ runs/
└─ scripts/
   ├─ benchmark_inventory.py
   ├─ evaluate_retrieval.py
   ├─ evaluate_rfp.py
   ├─ evaluate_strategy.py
   ├─ evaluate_qa.py
   └─ render_knowledge_docs.py
```

## Prompt Engineering Interventions

### RFP Analyzer
- JSON structured output
- requirement IDs
- source quote binding
- numeric fidelity
- fail-closed unknown policy

### Proposal Strategist
- requirement binding
- evidence binding
- RFP fact / reference fact / reference pattern / AI recommendation separation
- unsupported company claim blocking
- reference gap disclosure

### Proposal QA
- explicit error taxonomy
- BLOCK / WARN / INFO severity
- evidence-aware validation
- mandatory requirement coverage
- false-positive control

## Benchmark Gate Status

- [x] synthetic proposals 10~12종
- [x] proposal assets 50~80개
- [x] 신규 RFP 2종 추가
- [x] dev / holdout 분리 및 v1 freeze
- [x] hard-negative retrieval 난이도 검증
- [x] GitHub Actions reproducibility check
- [x] RFP Analyzer benchmark runner / raw recorder / aggregator / prompt diff 구축\n- [x] holdout 실행 보호 및 CI dry validation\n- [ ] 동일 frontier model / 동일 parameters에서 RFP Analyzer v0~v3 live raw run 저장
- [ ] RFP Analyzer / Strategist / QA evaluator 실행
- [ ] Prompt Engineering Before / After 결과 확정
- [ ] Dify Knowledge 실제 Retrieval Test
- [ ] 최종 RFP → 전략 → 목차 → 장표 초안 통합 Workflow

Prompt 개선 수치는 위 미완료 항목을 끝낸 뒤에만 위시켓 포트폴리오에 사용합니다.

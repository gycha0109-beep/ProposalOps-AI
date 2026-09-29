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
v1 Structured
   ↓
v2 Grounded
   ↓
v3 Guarded
   ↓
v4 Compact Grounded candidate
```

## Portfolio Navigation

- Wishket 요구사항 ↔ 저장소 증거: `docs/wishket-evidence-map.md`
- 3분 데모 가이드: `docs/demo-guide.md`
- Agent platform setup: `dify/setup-guide.md`
- Logical workflow blueprint: `dify/workflow-spec.yaml`
- RFP Analyzer failure analysis: `docs/prompt-failure-analysis/rfp-analyzer-dev-v1.md`

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

RFP Analyzer의 v0~v3 dev live raw run 8건은 완료됐습니다. v4는 prompt와 acceptance criteria를 먼저 고정했지만 Gemini 503/429 때문에 유효한 출력이 없어 `NOT_EVALUATED` 상태입니다. 따라서 아직 최종 production 개선율이나 holdout 성능은 주장하지 않습니다.


## Live Prompt Benchmark Model

RFP Analyzer의 현재 비교 benchmark는 **GPT-5.6 Luna**를 고정 모델로 사용합니다.

- provider: OpenAI Responses API
- model: `gemini-3.6-flash`
- reasoning effort: `low`
- measured dev runs: `2 RFP × v0~v3 = 8 raw outputs`
- v4: `NOT_EVALUATED` (provider 503/429)
- secret: `OPENAI_API_KEY`

provider 오류와 quota 실패도 raw evidence로 보존합니다. v4는 provider 응답을 얻지 못했기 때문에 acceptance를 통과/실패로 판정하지 않았습니다.

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
- prompt variants: **13**

## Proposal QA Result

GPT-5.6 Luna / reasoning low 기준으로 QA v4는 dev와 holdout 모두 통과했습니다.

- dev BLOCK recall: **100%**
- dev false positive: **0%**
- dev error type accuracy: **100%**
- dev severity accuracy: **100%**
- holdout BLOCK recall: **100%**
- holdout false positive: **0%**
- holdout error type accuracy: **100%**
- holdout severity accuracy: **100%**

Candidate: `proposal_qa/v4_compact_taxonomy.md`

> holdout 실행에서 이전 variants도 함께 실행된 기록은 보존하며, frozen v4는 holdout 결과를 본 뒤 수정하지 않습니다.

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
│  ├─ benchmark-validation.yml
│  ├─ rfp-analyzer-live.yml
│  ├─ proposal-qa-live.yml
│  └─ proposal-strategist-live.yml
├─ docs/
│  ├─ architecture.md
│  ├─ evaluation-methodology.md
│  ├─ prompt-engineering-case-study.md
│  ├─ retrieval-baseline.md
│  ├─ proposal-qa-benchmark-runner.md
│  ├─ proposal-strategist-benchmark-runner.md
│  ├─ wishket-evidence-map.md
│  └─ demo-guide.md
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
├─ dify/
│  ├─ workflow-spec.yaml
│  └─ setup-guide.md
├─ runs/
└─ scripts/
   ├─ benchmark_inventory.py
   ├─ evaluate_retrieval.py
   ├─ evaluate_rfp.py
   ├─ evaluate_strategy.py
   ├─ evaluate_qa.py
   └─ render_knowledge_docs.py
```


## Integration Workflow Status

production chain의 논리 계약은 현재 다음까지 연결돼 있습니다.

```text
RFP Analyzer
→ Retrieval Planner
→ Knowledge Retrieval
→ Evidence Builder
→ Proposal Strategist
→ Human Review
→ Pagination
→ Coverage Validator
→ Slide Draft iteration
→ Visual Prompt iteration
→ Proposal QA
→ Targeted Repair
→ Final Package
```

`dify/workflow-spec.yaml`은 특정 제품의 import DSL이 아니라 Dify/Antigravity 등에 옮길 수 있는 **논리 blueprint**입니다. 실제 플랫폼 node wiring과 live end-to-end 실행은 아직 남아 있습니다.

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
- [x] RFP Analyzer benchmark runner / raw recorder / aggregator / prompt diff 구축
- [x] holdout 실행 보호 및 CI dry validation
- [x] GPT-5.6 Luna 기준 RFP Analyzer v0~v3 dev raw run 8건 저장
- [x] RFP Analyzer evaluator 1.5 + grounding/truncation/canonical-schema metric 적용
- [x] v0→v1 구조화 개선 및 v2 grounding 효과 측정 (v1 schema 100%, v2 grounding 100% / schema 0%)
- [x] v3 truncation regression 분석
- [x] v4 prompt + dev acceptance criteria 사전 고정
- [ ] v4 dev 유효 출력 확보 (`NOT_EVALUATED`: provider 503/429)
- [ ] v4 candidate freeze 후 RFP-TEST-003 holdout 실행
- [x] Proposal QA neutral input fixture / evaluator / batch runner / aggregator / holdout gate 구축
- [x] Proposal QA dev acceptance criteria 사전 고정
- [x] Proposal QA GPT-5.6 Luna dev 비교 + v4 freeze + holdout 완료
- [x] Proposal Strategist neutral Evidence Pack / evaluator / batch runner / aggregator / holdout gate 구축
- [x] Proposal Strategist dev acceptance criteria 사전 고정
- [ ] Proposal Strategist GPT-5.6 Luna v4 dev acceptance + holdout 완료
- [x] Pagination / Coverage / Slide Draft / Visual Prompt / Targeted Repair production draft prompt 구축
- [x] Agent-platform logical workflow blueprint + setup guide 구축
- [ ] Dify Knowledge 실제 Retrieval Test
- [ ] Dify/Antigravity 실제 node wiring 및 end-to-end live demo

Prompt 개선 수치는 위 미완료 항목을 끝낸 뒤에만 위시켓 포트폴리오에 사용합니다.

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
세 개의 핵심 prompt track을 동일 benchmark에서 비교합니다.

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

평가 순서는 고정합니다.

```text
Synthetic data
      ↓
Gold assertions 작성
      ↓
Evaluation set freeze
      ↓
Baseline 실행
      ↓
Prompt variants 실행
      ↓
동일 evaluator로 비교
      ↓
Raw output + metrics 보존
```

결과를 본 뒤 같은 dataset version의 정답을 수정하지 않습니다. 오류 수정이 필요하면 dataset version을 올립니다.

현재 benchmark는 **pilot/dev 단계**이며 별도 holdout이 아직 없으므로 최종 Prompt Engineering 개선율은 주장하지 않습니다.

상세 규칙: `docs/evaluation-methodology.md`

## Current Assets

- synthetic proposals: 3
- proposal assets: 6
- synthetic RFP: 1
- retrieval gold queries: 6
- frozen RFP analyzer dev assertions: 10
- injected QA cases: 10
- prompt experiment tracks: 3
- prompt variants: 12

## Retrieval Baseline

작은 synthetic corpus에 대한 로컬 lexical baseline만 먼저 측정했습니다.

| Metric | Result |
|---|---:|
| Hit@1 | 100% |
| Hit@3 | 100% |
| Hit@5 | 100% |
| MRR | 1.000 |

이 값은 **6개 asset / 6개 query의 문자 n-gram TF-IDF baseline**이며 Dify Knowledge 또는 실제 업무 성능이 아닙니다.

## Repository Structure

```text
ProposalOps-AI/
├─ docs/
│  ├─ architecture.md
│  ├─ evaluation-methodology.md
│  └─ prompt-engineering-case-study.md
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
│  ├─ frozen/
│  │  ├─ dev/
│  │  └─ holdout/
│  └─ qa-injected-errors/
├─ runs/
└─ scripts/
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

## Next Benchmark Gate

최종 포트폴리오 비교 수치를 내기 전에 반드시 다음을 완료합니다.

1. synthetic proposals 10~12종으로 확대
2. proposal assets 50~80개로 확대
3. 신규 RFP 최소 2종 추가
4. dev와 분리된 holdout freeze
5. 동일 모델/파라미터에서 v0~v3 raw run 저장
6. evaluator 실행
7. 실패 케이스까지 공개

그 이후에만 Before / After 개선 수치를 위시켓 포트폴리오에 사용합니다.

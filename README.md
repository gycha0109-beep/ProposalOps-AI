# ProposalOps AI

공공기관 RFP와 과거 우수 제안서를 기반으로 **제안 전략 → 페이지네이션 → 장표별 초안 → 이미지 생성 프롬프트 → 근거 검증**까지 지원하는 제안서 작성 자동화 PoC입니다.

> 이 저장소의 샘플 데이터와 성과 수치는 포트폴리오 검증용 synthetic/demo 데이터입니다. 실제 고객 프로젝트 수행 실적으로 표현하지 않습니다.

## 문제 정의

공공기관 입찰 제안 업무에서는 신규 RFP를 분석하고, 과거 유사 제안서를 찾고, 전략과 목차를 설계한 뒤 장표별 초안을 작성하는 데 반복적인 시간이 소요됩니다.

ProposalOps AI는 과거 제안서를 단순히 문서 단위로 저장하지 않고 **재사용 가능한 제안 자산(Proposal Asset)** 으로 구조화하여, 신규 RFP의 요구사항과 연결합니다.

## 핵심 원칙

1. **Reference Grounding** — 회사 실적·수치·사례는 반드시 검색된 근거와 연결합니다.
2. **Semantic Assetization** — 제안서를 임의 토큰 단위가 아니라 페이지/섹션/전략 의미 단위로 구조화합니다.
3. **RFP-first Planning** — 문서를 받자마자 본문을 쓰지 않고 요구사항·평가기준·필수 산출물을 먼저 구조화합니다.
4. **Traceability** — 생성 결과가 어떤 RFP 항목과 과거 제안서 근거를 사용했는지 추적할 수 있게 합니다.
5. **Fail Closed** — 근거 없는 회사 실적·정량 수치는 생성하지 않고 `REFERENCE_NOT_FOUND`로 표시합니다.

## 목표 파이프라인

```text
과거 제안서 PDF/PPT
        ↓
텍스트 추출 / 정제 / 유형화
        ↓
Proposal Asset Dataset
        ↓
Knowledge Base
        ↓
신규 RFP
        ↓
RFP Analyzer
        ↓
Retrieval Planner
        ↓
Evidence Pack
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

## 현재 구현 범위

- [x] Proposal Taxonomy v0.1
- [x] 제안서 페이지 자산 스키마 예제
- [x] 테스트용 공공기관 RFP 샘플
- [x] Retrieval Gold Set 초안
- [ ] PDF/PPT 전처리 파이프라인
- [ ] Dify Knowledge Base 적재
- [ ] RFP Analyzer Prompt
- [ ] Retrieval Planner Prompt
- [ ] Proposal Strategist Prompt
- [ ] Pagination Prompt
- [ ] Slide Draft Prompt
- [ ] Proposal QA Prompt
- [ ] 통합 Evaluation

## Repository

```text
ProposalOps-AI/
├─ README.md
├─ docs/
│  └─ architecture.md
├─ data/
│  ├─ raw/
│  │  ├─ proposals/
│  │  └─ rfps/
│  ├─ processed/
│  │  └─ proposals/
│  └─ taxonomy/
│     └─ proposal-taxonomy.yaml
├─ prompts/
└─ evals/
   └─ retrieval-goldset.json
```

## 데이터 자산화 단위

각 제안서 페이지는 다음과 같은 자산으로 변환됩니다.

- 제안서/페이지 식별자
- 사업 카테고리
- 발주처 유형
- 페이지 유형
- 대상/목적/핵심 전략
- 산출물
- 차별화 요소
- 재사용 가능한 표현
- 회사 고유 사실 여부
- 출처 페이지
- 재사용 허용 수준

상세 필드는 `data/taxonomy/proposal-taxonomy.yaml`을 기준으로 합니다.

## 포트폴리오에서 증명할 것

단순히 “RAG가 답변한다”가 아니라 아래를 검증합니다.

- 신규 RFP에서 필수 요구사항을 빠짐없이 추출하는가
- 관련 과거 제안서 페이지가 검색되는가
- 제안 전략이 검색 근거를 실제로 반영하는가
- 회사 실적/수치가 근거 없이 생성되지 않는가
- 최종 장표 초안이 RFP 요구사항과 연결되는가

## 예정 평가 지표

아래 값은 목표치이며 실제 결과가 아닙니다.

| Metric | Target |
|---|---:|
| Retrieval Hit@5 | >= 90% |
| RFP mandatory requirement extraction recall | >= 95% |
| Citation coverage for factual claims | 100% |
| Unsupported quantitative claims | 0 |
| Missing mandatory proposal items | 0 |

실제 측정 결과는 `evals/` 아래에 별도로 기록합니다.

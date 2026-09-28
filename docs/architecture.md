# ProposalOps AI Architecture v0.1

## 1. 시스템 목적

ProposalOps AI는 과거 제안서의 표현을 단순 복사하는 도구가 아니라, 과거 수행 전략과 문서 패턴을 검색 가능한 지식자산으로 구조화하고 신규 RFP 요구사항에 맞춰 재조합하는 제안 지원 시스템이다.

## 2. 처리 단계

### A. Proposal Assetization

입력:
- 과거 우수 제안서 PDF/PPT

처리:
1. 텍스트 추출
2. 헤더/푸터/반복 문구 제거
3. 페이지 단위 구조 보존
4. 페이지 유형 분류
5. 사업 카테고리/대상/목적/전략/산출물 태깅
6. 회사 고유 사실과 일반 전략 아이디어 분리
7. source document/page 기록

출력:
- 검색 가능한 Proposal Asset

### B. RFP Analysis

RFP에서 아래 정보를 구조화한다.

- 사업 목적
- 사업 범위
- 대상
- 기간
- 예산
- 필수 산출물
- 평가 항목
- 제안서 작성 지침
- 필수 포함 항목
- 금지/제약 조건
- 제출 형식
- 확인이 필요한 모호한 요구사항

### C. Retrieval Planning

RFP의 각 요구사항을 검색 질의로 변환한다.

예:
- "청년층 대상 SNS 홍보 전략"
- "공공기관 숏폼 영상 운영"
- "참여형 캠페인"
- "성과 측정 KPI"

검색 결과는 Evidence Pack으로 정리한다.

### D. Proposal Strategy

Evidence Pack과 RFP를 분리하여 사용한다.

- RFP FACT: 발주 문서에 명시된 사실
- REFERENCE FACT: 과거 제안서에 실제 존재하는 사실
- AI RECOMMENDATION: 현재 RFP에 맞게 신규 제안한 내용

세 유형을 혼합해 사실처럼 표현하지 않는다.

### E. Pagination

각 페이지는 다음 계약을 갖는다.

- page_no
- section
- title
- page_goal
- key_message
- rfp_requirement_ids
- reference_ids
- content_blocks
- visual_direction

### F. Slide Draft

페이지별로:
- 헤드라인
- 서브 카피
- 핵심 본문
- 표/도식 구조
- 근거 참조
- 이미지 생성 프롬프트

를 생성한다.

### G. Proposal QA

검사 항목:
1. RFP requirement coverage
2. source citation validity
3. unsupported numerical claims
4. company-reference misuse
5. deliverable omission
6. section consistency
7. strategy-to-slide traceability

## 3. Grounding Policy

다음 정보는 근거가 없으면 생성 금지:

- 고객명
- 계약금액
- 매출/성과
- 참여자 수
- 프로젝트 기간
- 수상 실적
- 정량 개선치
- 회사 인력/조직/보유 장비
- 기존 수행 프로젝트

근거를 찾지 못한 경우:

`REFERENCE_NOT_FOUND`

로 반환한다.

## 4. Retrieval Unit

기본 검색 단위는 **proposal page asset**이다.

페이지 자체의 의미가 불완전한 경우 인접 페이지와 묶는 것을 허용하지만, source page provenance는 유지한다.

일반적인 arbitrary token chunking만 사용하는 방식은 피한다.

## 5. Traceability

최종 결과는 다음 연결을 유지해야 한다.

```text
RFP Requirement
   ↕
Proposal Page
   ↕
Reference Asset
```

따라서 특정 장표가:
- 왜 존재하는지
- 어떤 RFP 항목을 충족하는지
- 어떤 과거 자료를 참고했는지

추적 가능해야 한다.

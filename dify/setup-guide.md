# Agent Platform Setup Guide

이 문서는 ProposalOps AI를 Dify, Antigravity 또는 유사 AI-agent platform에 구현하기 위한 설정 가이드입니다.

> `workflow-spec.yaml`은 논리 blueprint이며 특정 플랫폼의 import 가능한 export 파일이 아닙니다. 제품별 UI/DSL 차이는 adapter 단계에서 처리합니다.

## 1. Knowledge Base 준비

과거 제안서를 PDF 단위로 바로 검색시키지 않고 **Proposal Asset** 단위로 자릅니다.

필수 metadata:

| Field | Type | Purpose |
|---|---|---|
| asset_id | string | provenance의 최소 단위 |
| proposal_id | string | 서로 다른 제안서 사실 혼합 방지 |
| category | string | PR/교육/영상/캠페인/행사 등 |
| client_type | string | 기관 유형 filtering |
| page_type | string | 전략/운영/KPI/리스크 등 |
| source_page | number | 원문 추적 |
| reuse_level | string | fact/pattern/copy 재사용 권한 |
| sensitivity | string | 공개/제한 구분 |

본문에는 objective, strategies, reusable_patterns, company_facts, normalized_text 등을 유지합니다.

## 2. RFP Analyzer

입력: 추출된 RFP text.

출력은 downstream node가 사용할 JSON이어야 합니다.

현재 benchmark 중인 production candidate는 아직 frozen 상태가 아니므로, 실제 고객 workflow에서는 candidate freeze 이후 연결합니다.

## 3. Retrieval Planner

RFP requirement별로 검색 intent를 분리합니다.

예:

```text
R-003 숏폼 기획
→ query: "30초 세로형 정책 숏폼 Hook 행동유도"
→ page_type filter: content_plan
→ category filter: video
```

한 query에 전략·운영·성과·리스크를 모두 섞지 않습니다.

## 4. Knowledge Retrieval

각 requirement별 검색을 반복 실행합니다.

검색 결과에는 최소:

- asset_id
- proposal_id
- source_page
- retrieval score
- 원문/normalized text

를 보존합니다.

## 5. Evidence Builder

검색 결과를 곧바로 Strategist에 넘기지 않습니다.

Evidence Builder가 다음을 판정합니다.

- direct
- partial
- pattern_only
- irrelevant

그리고 사용 가능 범위를 명시합니다.

```text
REFERENCE_PATTERN은
"과거 수행에서 42% 개선했다" 같은 회사 성과 claim으로 승격할 수 없음
```

## 6. Proposal Strategist

입력:

1. RFP analysis
2. Evidence Pack

모든 전략은 requirement와 연결하고, reference를 사용했다면 evidence ID를 남깁니다.

정보 클래스를 분리합니다.

- RFP_FACT
- REFERENCE_FACT
- REFERENCE_PATTERN
- AI_RECOMMENDATION

## 7. Human Review Gate

Strategist 뒤에 사람 승인 단계를 둡니다.

사용자는 다음을 확인합니다.

- 제안 컨셉
- 핵심 전략 축
- reference 해석
- client confirmation이 필요한 claim

승인 전에는 Pagination으로 진행하지 않습니다.

## 8. Pagination + Coverage

Pagination Planner가 페이지 구조를 만들고 Coverage Validator가 mandatory requirement 누락과 ID 오류를 차단합니다.

Coverage FAIL이면 전체 제안서를 다시 만들지 않고 오류 stage만 repair합니다.

## 9. Slide Draft / Visual Prompt

각 page를 iteration으로 처리합니다.

Slide Draft의 factual claim은 evidence ID를 유지합니다.

Visual Prompt의 `data_chart`는 실제 수치가 없으면 생성하지 않습니다.

## 10. Proposal QA

BLOCK 예:

- mandatory requirement 누락
- 회사 실적 조작
- 근거 없는 정량 수치
- 잘못된 evidence ID
- 서로 다른 proposal 사실 병합

WARN 예:

- page 목적/전략 불일치
- 반복 메시지
- 장표 과밀

## 11. Targeted Repair

오류 stage만 수정합니다.

```text
strategy error   → Strategist
pagination error → Pagination
slide error      → 해당 slide
visual error     → 해당 visual prompt
```

전체 regeneration은 최후 수단입니다.

## 12. Benchmark와 Production 분리

실험용 prompt와 production prompt를 섞지 않습니다.

```text
prompts/<track>/v0~vN
→ frozen dev benchmark
→ candidate freeze
→ holdout
→ production alias
```

현재 RFP Analyzer, Proposal Strategist, Proposal QA 모두 holdout gate가 코드로 잠겨 있습니다.

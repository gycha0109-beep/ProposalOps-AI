# 3-Minute Portfolio Demo Guide

목표: **"RFP를 넣으면 과거 제안서 근거를 추적하면서 전략·페이지·장표 초안까지 만들고, QA가 근거 없는 주장을 차단한다"**를 3분 안에 보여줍니다.

## 0:00–0:30 — RFP

입력: synthetic RFP 1개.

보여줄 것:

- 사업 기간/대상/산출물
- requirement IDs
- 숫자 보존
- 누락 값은 unknown
- 원문 source quote

실제 benchmark가 있는 영역만 수치를 말합니다.

## 0:30–1:00 — Reference Retrieval

requirement 하나를 선택합니다.

예:

```text
R-003 숏폼 영상 기획
→ PA-VIDEO-004-P021
→ 30초 Hook → Core → Action
```

여기서 핵심은 "비슷한 제안서를 찾았다"가 아니라 **어느 자산의 어느 패턴을 왜 쓰는지** 보여주는 것입니다.

## 1:00–1:30 — Evidence-bound Strategy

화면에서 다음 연결을 보여줍니다.

```text
Requirement
→ Evidence
→ Strategy
```

회사 실적 근거가 없으면 과거 성과처럼 표현하지 않고 AI_RECOMMENDATION 또는 reference gap으로 남깁니다.

## 1:30–2:00 — Pagination

Strategy를 실제 페이지 구조로 변환합니다.

보여줄 필드:

- page_goal
- key_message
- requirement IDs
- strategy IDs
- evidence IDs
- fact_risk

Coverage Validator가 누락 requirement를 차단하는 장면을 보여주면 좋습니다.

## 2:00–2:30 — Slide + Visual Prompt

페이지 한 장을 선택해:

- headline
- body blocks
- claim type
- evidence IDs
- visual type
- image/diagram prompt

를 보여줍니다.

실제 숫자가 없으면 data chart를 만들지 않는 guardrail을 강조합니다.

## 2:30–3:00 — QA / Repair

의도적으로 근거 없는 문장을 넣습니다.

예:

```text
"기존 청년 캠페인에서 참여율을 42% 향상했습니다."
```

company_facts에 근거가 없으므로 Proposal QA가 BLOCK해야 합니다.

그 다음 전체 제안서를 다시 만들지 않고 해당 slide만 Targeted Repair하는 흐름을 보여줍니다.

## 데모에서 말하면 안 되는 것

- synthetic 결과를 실제 고객 성과처럼 표현
- 아직 실행하지 않은 Strategist/QA benchmark 수치
- v4가 검증됐다고 표현
- logical workflow spec을 Dify import 파일이라고 표현

## 데모 완료 조건

- provenance chain을 한 번 이상 화면에 노출
- 하나 이상의 hallucination BLOCK 사례 노출
- raw benchmark/report 링크 제시
- synthetic/demo 데이터임을 명시

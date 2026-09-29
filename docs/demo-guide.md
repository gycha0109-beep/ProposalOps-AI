# 3-Minute Portfolio Demo Guide

목표: **“RFP를 분석하고 과거 제안서 근거를 연결해 전략·페이지·장표·시각화 초안을 만든 뒤, QA가 근거 범위를 초과한 주장까지 찾아 affected provenance chain만 수정한다.”**를 3분 안에 보여줍니다.

> 모든 데이터는 synthetic/demo입니다.

## 0:00–0:30 — Prompt Engineering Before / After

먼저 RFP Analyzer 비교표를 보여줍니다.

`reports/rfp-analyzer-dev-v1-gpt56luna.json`

핵심:

| Version | Assertion | Numeric | Requirement | Schema | Grounding |
|---|---:|---:|---:|---:|---:|
| v0 | 80.83% | 82.86% | 75% | 0% | 0% |
| v1 | 90.83% | 92.85% | 100% | 100% | 0% |
| v2 | 90.83% | 92.85% | 100% | 0% | 100% |
| v4 | **100%** | **100%** | **100%** | **100%** | **100%** |

설명:

- v1: 구조화로 requirement/schema 안정성 개선
- v2: grounding을 얻었지만 schema drift 발생
- v3: 규칙 추가만으로 문제를 해결하지 못함
- v4: fixed schema + compact grounding + explicit unknown으로 통합

holdout도 별도 실행했다는 것을 보여줍니다.

`reports/rfp-analyzer-holdout-v1-gpt56luna.json`

## 0:30–1:00 — Requirement → Evidence → Strategy

RFP-TEST-002에서 하나의 requirement를 선택합니다.

예:

```text
R-205 운영정보 검수
→ EV-R-205-01 / EV-R-205-02
→ PA-CAMP-010-P023 / PA-PR-011-P012
→ ST-05
```

보여줄 파일:

- `evals/strategist/inputs-v1.json`
- `runs/proposal_strategist/benchmark-v1-gpt56luna/dev/v4_explicit_classes/run-01.json`

핵심 메시지:

> 비슷한 문서를 통째로 복사하는 것이 아니라 requirement별 evidence와 재사용 범위를 연결합니다.

## 1:00–1:30 — Strategy → Pagination → Slide → Visual

최종 E2E package:

`runs/e2e-demo/RFP-TEST-002/final-package-repaired.json`

결과:

- 8 pages
- 8 slide drafts
- 8 visual specifications
- R-201~R-206 모두 COVERED

페이지 하나에서 다음을 보여줍니다.

- page_goal
- key_message
- requirement IDs
- strategy IDs
- evidence IDs
- body block claim_type
- visual specification

## 1:30–2:10 — Final QA가 실제 의미 범위 초과를 BLOCK

초기 QA:

`runs/e2e-demo/RFP-TEST-002/qa.json`

실제 BLOCK:

`PAGE-006`의 “공식 확인 채널 및 담당자” 표현은 연결 evidence가 직접 지원하지 않았습니다.

이후 repair cycle 2에서는 더 깊은 문제도 탐지했습니다.

`runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-2.json`

- ST-05/PAGE-006에 `제작 시점 확인` 표현 잔존
- ST-06/PAGE-008에 evidence가 없는 `시청` KPI 단계
- evidence가 없는 분석 축 추가

이 장면에서 강조할 것:

> QA는 evidence ID가 존재하는지만 검사한 것이 아니라, 해당 evidence가 **문장의 의미까지 실제로 지원하는지** 다시 검사했습니다.

## 2:10–2:45 — Provenance-chain Targeted Repair

Cycle 3:

`runs/e2e-demo/RFP-TEST-002/repair-cycle-3.json`

수정 범위:

```text
ST-05 / ST-06
→ PAGE-006 / PAGE-008
→ Slide
→ Visual
```

나머지 6개 page chain은 다시 생성하지 않았습니다.

수정 예:

```text
도달 → 시청 → 상세조회 → 저장 → ...
↓
도달 → 상세조회 → 저장 → 지도·코스·예약 페이지 이동
```

근거가 지원하지 않는 `시청` 단계를 제거했습니다.

## 2:45–3:00 — Final PASS

최종 QA:

`runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-3.json`

```json
{
  "status": "PASS",
  "issues": []
}
```

마지막으로 세 benchmark track이 모두 dev + holdout까지 끝났음을 보여줍니다.

- RFP Analyzer v4: frozen / holdout PASS
- Proposal Strategist v4: frozen / holdout PASS
- Proposal QA v4: frozen / holdout PASS

## 데모에서 말하면 안 되는 것

- synthetic benchmark를 실제 고객 성과처럼 표현
- 이 결과로 실제 제안 수주율이 개선됐다고 주장
- lexical retrieval baseline을 Dify/embedding retrieval 성능이라고 표현
- `dify/workflow-spec.yaml`을 import 가능한 공식 Dify DSL이라고 표현
- Pagination/Slide/Visual prompt가 별도 frozen benchmark까지 통과했다고 표현

## 데모 핵심 한 문장

> “생성 모델에게 제안서를 한 번에 맡긴 것이 아니라, RFP requirement와 과거 제안서 evidence를 ID로 연결하고 final QA가 의미 범위 초과까지 검증한 뒤 affected provenance chain만 재생성하는 구조로 만들었습니다.”

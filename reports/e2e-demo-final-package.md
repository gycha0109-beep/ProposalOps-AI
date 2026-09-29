# Final E2E Proposal Package — RFP-TEST-002

> Synthetic/demo output. 실제 고객 제안서가 아닙니다.

## Package summary

- project: **지역 문화·관광 디지털 홍보 사업**
- target: **20~40대 국내 개별 여행객, 지역 주민**
- duration: **계약일로부터 5개월**
- budget: **95,000,000원**
- final status: **PASS**
- final QA issues: **0**
- pages/slides/visuals: **8 / 8 / 8**

## Page plan

| No. | Page ID | Title | Requirement | Strategy | Visual | Fact risk |
|---:|---|---|---|---|---|---|
| 1 | PAGE-001 | 보고 싶은 곳에서, 이번 주말 갈 코스로 | — | ST-02, ST-05, ST-06 | process_diagram | low |
| 2 | PAGE-002 | 방문 동기와 상황에 따라 달라지는 타깃 전략 | R-201 | ST-01 | icon_diagram | medium |
| 3 | PAGE-003 | 발견 콘텐츠를 저장과 방문 계획으로 연결하는 구조 | R-202 | ST-02 | process_diagram | low |
| 4 | PAGE-004 | 첫 3초에 이해되고 하나의 행동으로 이어지는 숏폼 | R-203 | ST-03 | process_diagram | low |
| 5 | PAGE-005 | 공식 채널의 신뢰성과 지역 크리에이터의 체험성을 연결 | R-204 | ST-04 | icon_diagram | medium |
| 6 | PAGE-006 | 게시 전 확인하고 변경 시 함께 갱신하는 운영정보 검수 | R-205 | ST-05 | process_diagram | low |
| 7 | PAGE-007 | 5개월 운영 로드맵과 산출물 관리 | — | ST-01, ST-03, ST-04, ST-05 | process_diagram | low |
| 8 | PAGE-008 | 도달을 넘어 방문 의도를 측정하는 단계형 KPI | R-206 | ST-06 | data_chart | low |

## Requirement coverage

- `R-201` → `PAGE-002` — **COVERED**
- `R-202` → `PAGE-003` — **COVERED**
- `R-203` → `PAGE-004` — **COVERED**
- `R-204` → `PAGE-005` — **COVERED**
- `R-205` → `PAGE-006` — **COVERED**
- `R-206` → `PAGE-008` — **COVERED**

## Provenance repair example

### R-205 / ST-05 / PAGE-006

Final strategy:

> 휴관, 매진, 운영시간, 행사 일정 등 변경 가능한 항목을 게시 전에 확인한다. 변경이 발생하면 기존 게시물과 연결된 코스·카드·크리에이터 콘텐츠의 상태를 함께 갱신하고 변경 정보의 버전을 표시한다.

Evidence:

- `EV-R-205-01` / `PA-CAMP-010-P023`: 휴관, 매진, 일정 변경을 게시 전 확인하고 변경 시 기존 게시물의 상태를 함께 갱신한다.
- `EV-R-205-02` / `PA-PR-011-P012`: 접수기간, 지원금액, 자격 조건처럼 변경 가능성이 있는 항목을 게시 전 별도 확인한다.

### R-206 / ST-06 / PAGE-008

Final strategy:

> 월별 보고와 최종 보고에서 도달, 상세조회, 저장, 지도·코스·예약 페이지 이동 등 방문 의도에 가까운 행동을 단계별로 측정한다. 측정 결과를 다음 제작 우선순위와 코스 구성 개선에 활용한다.

Evidence:

- `EV-R-206-01` / `PA-PR-007-P019`: 노출 외에 저장, 지도 클릭, 코스 페이지 이동 등 방문 의도에 가까운 행동을 측정한다.
- `EV-R-206-02` / `PA-CAMP-010-P024`: 콘텐츠 도달, 프로그램 상세조회, 일정 저장, 예약 페이지 이동을 단계별로 측정한다.

## Final QA

```json
{
  "status": "PASS",
  "issues": [],
  "summary": "제공된 RFP 요구사항은 모두 페이지에 반영되어 있으며, 회사 실적·정량 성과의 무근거 주장이나 유효하지 않은 evidence 연결이 확인되지 않았습니다. 이전 INVALID_REFERENCE 이슈도 chain repair output에서 수정된 상태로 반영되어 있습니다."
}
```

## Repair history

- cycle 1: page-level repair
- cycle 2: page-level repair
- cycle 3: strategy_to_visual

Full raw package:

`runs/e2e-demo/RFP-TEST-002/final-package-repaired.json`

Detailed repair narrative:

`reports/e2e-demo-summary.md`

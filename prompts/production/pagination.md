# Production Draft — Pagination Planner

Status: **LIVE INTEGRATION VALIDATED — NOT FROZEN**


## Validation status

RFP-TEST-002 live E2E와 Dify Phase 3 integration에서 실제 사용되었습니다. Phase 3에서는 6개 requirement가 6개 page에 연결되고 deterministic Coverage Gate가 blocking error 0 / warning 0으로 PASS했습니다.

이 prompt는 전용 frozen benchmark/holdout을 별도로 수행하지 않았으므로 benchmark-frozen production prompt로 표현하지 않습니다.

입력:
1. RFP Analyzer 결과
2. Proposal Strategy
3. Evidence Pack
4. 제안서 페이지 수 또는 분량 제약(있는 경우)

목표는 전략을 실제 제안서 페이지 구조로 변환하는 것입니다.

## Rules

1. 모든 mandatory RFP requirement는 최소 하나의 page에 연결합니다.
2. 한 page는 하나의 명확한 page_goal과 하나의 key_message를 가집니다.
3. 근거 없는 회사 실적·성과·고객명·정량 수치를 페이지 메시지에 추가하지 않습니다.
4. evidence가 없는 신규 제안은 AI recommendation으로 취급합니다.
5. 평가 배점이 높은 요구사항은 한 페이지에 과도하게 압축하지 않습니다.
6. 동일 핵심 메시지의 반복 페이지를 만들지 않습니다.
7. page_no는 1부터 순차 증가시킵니다.
8. 입력에 총 페이지 수 제한이 있으면 이를 준수하고, 불가능하면 planning_warnings에 남깁니다.

## Output

JSON만 출력합니다.

{
  "pages": [
    {
      "page_id": "PAGE-001",
      "page_no": 1,
      "section": "string",
      "page_type": "string",
      "title": "string",
      "page_goal": "string",
      "key_message": "string",
      "rfp_requirement_ids": ["R-001"],
      "strategy_ids": ["ST-01"],
      "evidence_ids": ["EV-R-001-01"],
      "content_blocks": [
        {
          "role": "string",
          "intent": "string"
        }
      ],
      "visual_direction": "string",
      "fact_risk": "low | medium | high"
    }
  ],
  "requirement_coverage": [
    {
      "requirement_id": "R-001",
      "page_ids": ["PAGE-001"],
      "status": "COVERED | PARTIAL | MISSING"
    }
  ],
  "planning_warnings": []
}

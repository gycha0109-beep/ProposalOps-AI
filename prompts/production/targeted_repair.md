# Production Draft — Targeted Repair

Status: **LIVE REPAIR EXERCISED — NOT FROZEN**


## Validation status

RFP-TEST-002 live E2E와 Dify Phase 4 중간 검증 run에서 실제 사용되었습니다. Phase 4에서는 QA issue를 page/strategy scope로 라우팅하고 수정 후 deterministic gates와 QA recheck를 다시 수행했습니다. 최신 최종 성공 run은 강화된 생성 계약 덕분에 repair 0회로 PASS했습니다.

repair 동작은 live에서 exercise 되었지만 전용 frozen benchmark/holdout은 없으므로 benchmark-frozen prompt로 표현하지 않습니다. Python authoritative runner는 최대 3회 bounded repair 후에도 BLOCK이 남으면 escalation으로 종료합니다.

입력:
1. QA error 1개 또는 동일 원인의 error 묶음
2. 오류가 발생한 stage의 현재 output
3. 관련 RFP / Evidence / Strategy context

목표는 실패한 부분만 수정하고 이미 통과한 결과는 보존하는 것입니다.

## Routing

- strategy requirement/evidence 오류 → Proposal Strategist
- page coverage/structure 오류 → Pagination Planner
- slide factual claim/body 오류 → 해당 Slide Draft만
- visual factual/data 오류 → 해당 Visual Prompt만

## Rules

1. QA가 지적하지 않은 다른 page/stage를 다시 생성하지 않습니다.
2. 기존 ID를 가능한 한 유지합니다.
3. BLOCK 원인을 제거했는지 repair_summary에 명시합니다.
4. 새로운 factual claim을 추가할 때는 evidence가 필요합니다.
5. 근거가 없으면 삭제하거나 AI_RECOMMENDATION / client confirmation으로 전환합니다.
6. 수정 범위를 넓혀야만 해결 가능한 경우 escalation_required=true로 반환합니다.

## Output

JSON만 출력합니다.

{
  "target_stage": "strategy | pagination | slide | visual",
  "target_ids": ["PAGE-001"],
  "repaired_output": {},
  "repair_summary": [
    {
      "error_code": "string",
      "change": "string",
      "resolved": true
    }
  ],
  "escalation_required": false,
  "escalation_reason": null
}

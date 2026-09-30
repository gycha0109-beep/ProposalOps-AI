# Production Draft — Slide Draft Generator

Status: **LIVE INTEGRATION VALIDATED — NOT FROZEN**


## Validation status

RFP-TEST-002 live E2E와 Dify Phase 4 final-package run에서 실제 사용되었습니다. 최신 Phase 4 성공 run은 6개 page → 6개 slide, deterministic Slide Provenance Gate PASS, final Proposal QA PASS / issues 0이었습니다.

이 prompt는 live integration에서 검증되었지만 전용 frozen benchmark/holdout을 별도로 수행하지 않았으므로 benchmark-frozen prompt로 표현하지 않습니다. Phase 4에서는 evidence scope를 upstream strategy/page wording보다 우선하도록 integration contract를 추가해 사용합니다.

입력:
1. 승인된 Pagination page 1개
2. 관련 Proposal Strategy
3. 관련 Evidence Pack
4. RFP 원문 요구사항

목표는 한 page의 실제 제안서 텍스트 초안을 만드는 것입니다.

## Rules

1. 입력 page의 page_goal과 key_message를 변경하지 않습니다.
2. factual claim은 evidence가 있을 때만 사용합니다.
3. evidence가 없는 신규 아이디어는 AI_RECOMMENDATION으로 분리합니다.
4. 회사 실적·고객명·성과 수치·계약금액을 임의 생성하지 않습니다.
5. evidence가 pattern_only면 "과거 수행 실적"으로 표현하지 않습니다.
6. 한 장표에 핵심 메시지를 하나만 둡니다.
7. 장문 문단보다 짧은 content block을 사용합니다.
8. 확인이 필요한 정보는 client_confirmation_required=true로 표시합니다.
9. Pagination에 없는 새 requirement를 임의 추가하지 않습니다.

## Output

JSON만 출력합니다.

{
  "page_id": "PAGE-001",
  "headline": "string",
  "subheadline": "string",
  "body_blocks": [
    {
      "label": "string",
      "text": "string",
      "claim_type": "RFP_FACT | REFERENCE_FACT | REFERENCE_PATTERN | AI_RECOMMENDATION",
      "evidence_ids": ["EV-R001-01"],
      "client_confirmation_required": false
    }
  ],
  "evidence_ids": [],
  "visual_type": "none | icon_diagram | process_diagram | illustration | photo | data_chart | reference_image",
  "speaker_note": "string",
  "fact_risk": "low | medium | high"
}

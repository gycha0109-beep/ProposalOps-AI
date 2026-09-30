# Production Draft — Visual Prompt Generator

Status: **LIVE INTEGRATION VALIDATED — NOT FROZEN**


## Validation status

RFP-TEST-002 live E2E와 Dify Phase 4 final-package run에서 실제 사용되었습니다. 최신 Phase 4 성공 run은 6개 slide → 6개 visual spec, deterministic Visual Provenance Gate PASS, final Proposal QA PASS / issues 0이었습니다.

이 prompt는 live integration에서 검증되었지만 전용 frozen benchmark/holdout을 별도로 수행하지 않았으므로 benchmark-frozen prompt로 표현하지 않습니다. Phase 4에서는 slide/page에 존재하는 수치만 재사용하고 data_chart에는 실제 quantitative input이 필요하도록 integration contract를 추가해 사용합니다.

입력:
1. Slide Draft
2. Pagination visual_direction
3. 사용 가능한 evidence/reference image metadata(있는 경우)

목표는 장표용 시각물 생성 또는 다이어그램 제작 지시를 만드는 것입니다.

## Rules

1. visual_type은 입력 Slide Draft의 허용 enum 안에서 선택합니다.
2. data_chart는 입력에 실제 수치 데이터가 있을 때만 허용합니다.
3. 실제 수치가 없으면 차트 숫자·비율·축 값을 생성하지 않습니다.
4. reference image가 없는데 실제 과거 행사/고객 현장 사진처럼 보이게 지시하지 않습니다.
5. AI illustration은 실제 수행 증거처럼 오인되지 않도록 표현합니다.
6. process_diagram은 단계와 연결 관계를 명시합니다.
7. 시각물이 필요하지 않으면 do_not_generate=true로 반환합니다.
8. 이미지 안에 긴 본문 텍스트를 넣지 않습니다.

## Output

JSON만 출력합니다.

{
  "page_id": "PAGE-001",
  "visual_type": "process_diagram",
  "do_not_generate": false,
  "purpose": "string",
  "image_prompt": "string | null",
  "diagram_spec": {
    "nodes": [],
    "edges": []
  },
  "data_source": [],
  "prohibited_elements": [],
  "fact_risk": "low | medium | high"
}

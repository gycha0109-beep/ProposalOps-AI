# Production Draft — Visual Prompt Generator

Status: **INTEGRATION DRAFT**

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

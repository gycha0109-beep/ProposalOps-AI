# RFP Analyzer — v1 Structured

## Experimental status
비교 실험용 variant.

## Intervention
v0에 **고정 JSON 구조와 requirement ID**를 추가한다.

## Prompt

RFP에서 사업 정보와 요구사항을 추출한다. 제안 전략은 작성하지 않는다.

JSON만 출력한다.

필드:
- project.name
- project.purpose[]
- project.target_audience[]
- project.duration
- project.budget
- scope[]
- deliverables[]
- requirements[]
- evaluation[]
- constraints[]

requirements의 각 항목에는 R-001부터 순차 ID를 부여한다.
deliverables에는 name, quantity, frequency를 기록한다.

문서에서 찾을 수 없는 값은 빈 문자열로 둔다.

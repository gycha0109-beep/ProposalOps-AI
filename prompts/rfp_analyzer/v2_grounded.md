# RFP Analyzer — v2 Grounded

## Experimental status
비교 실험용 variant.

## Intervention
v1에 **source grounding과 numeric fidelity**를 추가한다.

## Prompt

RFP에 명시적으로 존재하는 내용만 구조화한다. 제안 전략이나 추정 정보는 추가하지 않는다.

JSON만 출력한다.

각 scope, deliverable, requirement, evaluation, constraint에는 원문 근거인 `source_quote`를 포함한다.

규칙:
1. 수량, 기간, 예산, 배점은 원문 표현을 보존한다.
2. 요구사항마다 R-001 형식의 ID를 부여한다.
3. 서로 다른 요구사항을 임의로 합치지 않는다.
4. 해석이 필요한 내용은 `interpretation_note`에 분리한다.
5. 문서에 없는 회사 실적이나 수행 전략을 추가하지 않는다.

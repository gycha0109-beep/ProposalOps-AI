# Proposal Strategist — v1 Reference-aware

## Experimental status
비교 실험용 variant.

## Intervention
v0에 **RFP 요구사항과 retrieved reference를 명시적 입력으로 분리**한다.

## Prompt

입력:
1. RFP requirements
2. retrieved proposal references

두 입력을 참고해 제안 방향, 핵심 컨셉, 전략 3~4개를 작성한다.

각 전략에는:
- strategy_id
- name
- objective
- related_requirement_ids
- used_reference_ids
- execution_ideas

를 포함한다.

과거 자료를 사용하지 않은 신규 아이디어도 허용한다.

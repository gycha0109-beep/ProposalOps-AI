# Proposal QA — v1 Rules

## Experimental status
비교 실험용 variant.

## Intervention
v0에 **오류 taxonomy와 severity**를 추가한다.

## Error Types
- MISSING_REQUIREMENT
- UNSUPPORTED_CLAIM
- INVALID_REFERENCE
- CROSS_PROPOSAL_MERGE
- STRATEGY_PAGE_MISMATCH
- DUPLICATE_MESSAGE
- OVERLONG_SLIDE

## Severity
- BLOCK
- WARN
- INFO

## Prompt

RFP 요구사항과 제안서 초안을 비교해 오류를 탐지한다.
각 오류는 code, severity, page_id, claim, reason, action을 포함한다.

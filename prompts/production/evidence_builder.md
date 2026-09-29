# Production — Evidence Pack Builder

입력:
1. RFP Analyzer 결과
2. Retrieval Planner 결과
3. 검색된 Proposal Assets

목표는 검색 결과를 그대로 쓰는 것이 아니라 **실제 사용 가능한 근거인지 검증**하는 것이다.

## Support levels

- direct
- partial
- pattern_only
- irrelevant

## Status

- SUPPORTED
- PARTIAL_REFERENCE_ONLY
- NO_REFERENCE_FOUND

## Rules

- company_facts에 없는 회사 실적·고객명·성과 수치는 사실 근거로 사용하지 않는다.
- 서로 다른 proposal의 사실을 하나의 수행 사례처럼 합치지 않는다.
- asset_id, proposal_id, source_page를 유지한다.
- 각 evidence에 supported_point, allowed_use, prohibited_use를 기록한다.

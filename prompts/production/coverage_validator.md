# Production Draft — Coverage Validator

Status: **INTEGRATION DRAFT**

입력:
1. RFP requirements
2. Pagination Planner 결과
3. Proposal Strategy IDs
4. Evidence Pack IDs

목표는 제안서 페이지 생성 전에 구조적 누락과 잘못된 참조를 차단하는 것입니다.

## BLOCK

- mandatory requirement가 어느 page에도 연결되지 않음
- 존재하지 않는 requirement_id
- 존재하지 않는 strategy_id
- 존재하지 않는 evidence_id
- 한 page가 서로 무관한 핵심 목표를 과도하게 혼합
- factual company claim을 요구하면서 evidence가 없음

## WARN

- 하나의 page에 requirement가 과도하게 집중
- 같은 key_message가 여러 page에 반복
- 고배점 requirement의 페이지 비중이 지나치게 낮음
- fact_risk=high인데 evidence가 부족함

## Output

JSON만 출력합니다.

{
  "status": "PASS | FAIL",
  "blocking_errors": [
    {
      "code": "string",
      "page_id": "PAGE-001 | null",
      "requirement_id": "R-001 | null",
      "reason": "string",
      "action": "string"
    }
  ],
  "warnings": [],
  "coverage_summary": {
    "total_requirements": 0,
    "covered": 0,
    "partial": 0,
    "missing": 0
  }
}

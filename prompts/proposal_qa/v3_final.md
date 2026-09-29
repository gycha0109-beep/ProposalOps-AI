# Proposal QA — v3 Final

## Experimental status
현재 production candidate이며 비교 실험용 final variant다.

## Interventions
- explicit error taxonomy
- severity classification
- evidence-aware validation
- mandatory coverage check
- fail-closed critical rule
- false-positive control

## Blocking Errors
- mandatory RFP requirement 누락
- 존재하지 않는 회사 실적
- 근거 없는 정량 수치
- 존재하지 않거나 claim을 지원하지 않는 evidence_id
- 서로 다른 proposal의 회사 사실 혼합

## Warning Errors
- 전략과 페이지 목적 불일치
- 핵심 메시지 중복
- 장표 과밀
- visual direction 누락

## Rules
1. AI_RECOMMENDATION 자체를 회사 실적 오류로 오판하지 않는다.
2. 명확한 evidence가 있는 claim은 오류로 표시하지 않는다.
3. 근거가 불완전하면 BLOCK과 WARN을 구분한다.
4. 오류가 없는 항목을 억지로 생성하지 않는다.
5. 모든 BLOCK에는 재현 가능한 reason과 action을 남긴다.

## Output
JSON만 출력한다.

필수 필드:
- status: PASS | FAIL
- blocking_errors[]
- warnings[]
- requirement_coverage
- citation_coverage
- checked_claim_count

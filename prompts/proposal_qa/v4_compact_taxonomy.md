# Proposal QA — v4 Compact Taxonomy

## Experimental status
GPT-5.6 Luna dev benchmark용 candidate. v1의 명시적 taxonomy와 v3의 evidence-aware / false-positive control을 결합한다.

## Prompt

RFP 요구사항, Evidence Pack, Proposal Strategy, Slide Draft를 검토해 오류를 탐지한다.

허용하는 error type은 아래 7개뿐이다.

- MISSING_REQUIREMENT
- UNSUPPORTED_CLAIM
- INVALID_REFERENCE
- CROSS_PROPOSAL_MERGE
- STRATEGY_PAGE_MISMATCH
- DUPLICATE_MESSAGE
- OVERLONG_SLIDE

Severity는 아래만 사용한다.

- BLOCK
- WARN
- INFO

판정 규칙:
1. mandatory RFP requirement 누락은 MISSING_REQUIREMENT / BLOCK.
2. company_facts에 없는 회사 실적·성과·정량 수치는 UNSUPPORTED_CLAIM / BLOCK.
3. 존재하지 않거나 claim을 실제 지원하지 않는 evidence/reference는 INVALID_REFERENCE / BLOCK.
4. 서로 다른 proposal의 사실이나 패턴을 하나의 검증된 수행사례처럼 합치면 CROSS_PROPOSAL_MERGE / BLOCK.
5. page_goal과 실제 메시지가 불일치하면 STRATEGY_PAGE_MISMATCH / WARN.
6. AI_RECOMMENDATION 자체를 회사 실적으로 오판하지 않는다.
7. REFERENCE_PATTERN을 패턴으로만 재사용한 경우 오류가 아니다.
8. 명확한 evidence가 있는 claim은 오류로 표시하지 않는다.
9. 오류가 없는 항목을 억지로 생성하지 않는다.
10. 위 taxonomy 밖의 새로운 error type을 만들지 않는다.

각 판정은 제공된 RFP / evidence / company_facts / draft context만 사용한다.

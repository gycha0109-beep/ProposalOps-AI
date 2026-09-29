# Proposal QA — v2 Evidence-aware

## Experimental status
비교 실험용 variant.

## Intervention
v1에 **Evidence Pack과 Proposal Asset provenance 검증**을 추가한다.

## Prompt

입력:
1. RFP requirements
2. Evidence Pack
3. Proposal Strategy
4. Slide Drafts

검사:
- 모든 mandatory requirement가 최소 하나의 page에 연결되는가
- factual claim의 evidence_id가 실제 존재하는가
- evidence가 해당 claim을 실제로 지원하는가
- company_facts에 없는 회사 실적/정량 성과가 생성됐는가
- 서로 다른 proposal의 사실이 하나의 수행 사례로 합쳐졌는가

근거가 불충분한 factual claim은 BLOCK으로 처리한다.

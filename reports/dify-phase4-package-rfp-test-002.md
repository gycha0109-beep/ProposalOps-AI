# Dify Phase 4 — Final Package

- RFP: RFP-TEST-002
- status: **ESCALATION_REQUIRED**
- model: gpt-5.6-luna
- pages: **6**
- slides: **6**
- visuals: **6**
- repair cycles: **2**

## Deterministic gates

- coverage: **PASS**
- slide provenance: **PASS**
- visual provenance: **PASS**
- broken provenance chains: **0**

## Semantic QA

- status: **FAIL**
- issues: **2**
- summary: 필수 요구사항과 수량·보고 산출물 커버리지는 충족하지만, PAGE-003에서 EV-R-203-01이 직접 지원하지 않는 표현이 reference claim으로 확장되어 인용 범위를 초과한다.

## Requirement → Asset → Evidence → Strategy → Page

- R-201 → PA-PR-007-P015 → EV-R-201-01 → ST-01 → PAGE-001
- R-202 → PA-PR-007-P016 → EV-R-202-01 → ST-02 → PAGE-002
- R-203 → PA-VIDEO-004-P021 → EV-R-203-01 → ST-03 → PAGE-003
- R-204 → PA-PR-007-P018 → EV-R-204-01 → ST-04 → PAGE-004
- R-205 → PA-CAMP-010-P023 → EV-R-205-01 → ST-05 → PAGE-005
- R-206 → PA-CAMP-010-P024 → EV-R-206-01 → ST-06 → PAGE-006

## Repair history

- cycle 1: scope=strategy_to_visual pages=['PAGE-002', 'PAGE-005', 'PAGE-006'] strategies=['ST-02', 'ST-05', 'ST-06']
- cycle 2: scope=strategy_to_visual pages=['PAGE-002'] strategies=['ST-02']

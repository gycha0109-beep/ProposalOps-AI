# Dify Phase 3 — Pagination + Coverage Gate

## Goal

Phase 2에서 검증한 grounded strategy를 제안서 페이지 구조로 변환하고, Slide Draft 생성 전에 구조적 누락과 잘못된 참조를 deterministic gate로 차단한다.

```text
RFP
→ Retrieval
→ Evidence
→ Strategy
→ Pagination Planner
→ Coverage Validator
```

모든 입력과 benchmark evidence는 synthetic/demo 데이터다.

## Live result

RFP: `RFP-TEST-002`

Source:

`reports/dify-phase2-core-rfp-test-002.json`

Model:

`gpt-5.6-luna` / reasoning low

Pagination:

- OpenAI call: 1
- page limit: 8
- generated pages: 6

Coverage Gate:

- implementation: deterministic Python
- total requirements: 6
- covered: 6
- missing: 0
- blocking errors: 0
- warnings: 0
- status: **PASS**

## Requirement → Page

| Requirement | Page | Strategy | Evidence |
|---|---|---|---|
| R-201 | PAGE-001 | ST-01 | EV-R-201-01 |
| R-202 | PAGE-002 | ST-02 | EV-R-202-01 |
| R-203 | PAGE-003 | ST-03 | EV-R-203-01 |
| R-204 | PAGE-004 | ST-04 | EV-R-204-01 |
| R-205 | PAGE-005 | ST-05 | EV-R-205-01 |
| R-206 | PAGE-006 | ST-06 | EV-R-206-01 |

## Why Coverage Validator is code, not another LLM

이 단계가 검사하는 값은 이미 canonical structured ID다.

- requirement_id
- strategy_id
- evidence_id
- page_id
- page_no

따라서 구조적 누락과 잘못된 연결은 LLM judge보다 deterministic code가 더 적합하다.

장점:

1. 동일 입력에 동일 판정
2. 추가 모델 비용 없음
3. invalid reference를 정확하게 BLOCK
4. CI에서 재현 가능
5. Dify Code node로 그대로 이식 가능

## Blocking checks

- no pages
- page limit exceeded
- duplicate/non-sequential page identifiers
- mandatory requirement missing
- invalid requirement_id
- invalid strategy_id
- invalid evidence_id
- strategy/page requirement mismatch
- reference-based strategy without attached evidence
- evidence/page requirement mismatch
- orphan evidence
- inconsistent requirement_coverage summary

Warnings:

- requirement density
- duplicate key message
- high fact risk without evidence

## Evidence

Live result:

- `reports/dify-phase3-pagination-rfp-test-002.json`
- `reports/dify-phase3-pagination-rfp-test-002.md`
- `runs/dify/phase3/RFP-TEST-002/phase3-result.json`

Implementation:

- `scripts/lib/pagination_eval.py`
- `scripts/run_dify_phase3_pagination.py`
- `configs/dify-phase3-pagination-v1.json`
- `.github/workflows/dify-phase3-pagination.yml`

## Dify Studio candidate

Current Dify DSL 0.7.0 candidate:

`dify/proposalops-phase3-pagination.yml`

It extends Phase 2 with:

```text
Proposal Strategist
→ Pagination Planner [LLM]
→ Coverage Validator [Code]
→ End
```

Static validator:

`scripts/validate_dify_phase3_dsl.py`

Expected graph:

- nodes: 16
- edges: 14
- LLM nodes: 5
- Code nodes: 6
- Knowledge Retrieval: 1
- serial query iteration: 1
- secrets embedded in DSL: 0

The Studio app itself has not been imported/smoke-tested with the user's account session yet. Static structure and live API-side logic are validated separately.

## Next

Next downstream stage:

```text
Pagination PASS
→ Slide Draft
→ Visual Prompt
→ Proposal QA
→ targeted repair if needed
```

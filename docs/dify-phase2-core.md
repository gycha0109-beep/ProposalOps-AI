# Dify Phase 2 — Grounded Strategy Core

## Goal

실제 Dify Knowledge semantic retrieval을 RFP 분석과 Evidence Builder, Proposal Strategist 사이에 연결해 다음 체인을 검증한다.

```text
RFP
→ RFP Analyzer
→ Retrieval Planner
→ Dify Production Knowledge
→ Evidence Builder
→ Proposal Strategist
```

모든 데이터는 synthetic/demo다.

## Live result

RFP: `RFP-TEST-002`

Knowledge:

- dataset: `ProposalOps Production v1`
- dataset id: `21dcb1f3-270f-4991-bcf8-b2782e6cf814`
- indexing: High Quality
- retrieval: semantic search
- corpus: 51 normal Proposal Assets
- hard negatives: 0

Retrieval Planner는 requirement마다 서로 다른 query를 정확히 2개 만든다.

각 requirement 처리:

```text
2 semantic queries
→ Dify top-5 retrieval
→ asset dedupe
→ intent → page_type deterministic filter
→ top-5 candidate pack
→ Evidence Builder
```

## RFP-TEST-002 result

Phase 2 Core: **PASS**

| Validation | Result |
|---|---:|
| RFP Analyzer requirement IDs | PASS |
| Retrieval Planner contract | PASS |
| Evidence result coverage | 100% |
| Evidence primary asset recall | 100% |
| Evidence selected asset precision | 100% |
| Evidence prohibited asset rejection | 100% |
| Evidence provenance validity | 100% |
| Evidence status accuracy | 100% |
| Unsupported company fact | 0 |
| Unsupported numeric claim | 0 |
| Strategist requirement coverage | 100% |
| Strategist evidence citation coverage | 100% |
| Strategist evidence validity | 100% |
| Information-class separation | 100% |
| Invalid evidence reference | 0 |
| Broken provenance chain | 0 |

Final evidence selection:

| Requirement | Evidence |
|---|---|
| R-201 | PA-PR-007-P015 |
| R-202 | PA-PR-007-P016 |
| R-203 | PA-VIDEO-004-P021 |
| R-204 | PA-PR-007-P018 |
| R-205 | PA-CAMP-010-P023 |
| R-206 | PA-CAMP-010-P024 |

Evidence:

- `reports/dify-phase2-core-rfp-test-002.json`
- `reports/dify-phase2-core-rfp-test-002.md`
- `runs/dify/phase2/RFP-TEST-002/core-workflow.json`

## Evidence Builder benchmark

Phase 2 전에 Evidence Builder 자체를 실제 Dify semantic top-5 결과로 검증했다.

Frozen candidate:

`v1_grounded`

결과:

| Version | Primary recall | Precision | Provenance | Status | PASS |
|---|---:|---:|---:|---:|---:|
| v0_baseline | 100% | 81.82% | 0% | 100% | 0% |
| v1_grounded | 100% | 100% | 100% | 100% | 100% |

Candidate:

`evals/frozen/v1/evidence-builder-candidate.json`

Production prompt:

`prompts/production/evidence_builder.md`

## Retrieval Planner lesson

첫 integration run에서는 한 requirement당 첫 query 하나만 사용했다.

그 결과 query 표현 변동에 따라 R-203 숏폼 reference가 top-5에서 빠지는 run이 발생했다.

수정:

1. requirement마다 query를 정확히 2개 생성
2. semantic mechanism query + keyword/format anchor query로 역할 분리
3. 두 Dify 결과를 asset_id 기준 merge
4. intent에 따라 page_type을 deterministic filter
5. Evidence Builder가 실제 내용 기준으로 최종 선택

이후 RFP-TEST-002 전체가 PASS했다.

## Provenance chain

최종 전략은 다음 연결을 보존한다.

```text
RFP Requirement
→ Retrieval queries
→ Dify Proposal Asset
→ Evidence ID
→ Strategy ID
```

예:

```text
R-205
→ 운영정보 변경 / 게시 전 확인 queries
→ PA-CAMP-010-P023
→ EV-R-205-01
→ ST-05
```

## Current Dify product boundary

현재 저장소에서 실제 완료된 것은:

- Dify Cloud Knowledge dataset 실제 업로드
- Dify Service API 실제 semantic retrieval
- OpenAI provider + text-embedding-3-small을 사용하는 High Quality retrieval
- RFP-TEST-002 grounded strategy core live PASS

Dify Studio의 **App/Workflow DSL import는 Knowledge Service API key로 수행하지 않는다**.

현재 Dify main 기준 App DSL import API는 workspace write 권한의 Account OAuth subject를 요구한다.
따라서 repository의 Service API secret만으로 사용자의 Studio에 앱을 생성했다고 주장하지 않는다.

다음 작업은 current Dify DSL 0.7.0 기준 import candidate를 만들고 구조 검증한 뒤,
사용자 Dify Studio에서 import하여 실제 node UI smoke test를 수행하는 것이다.

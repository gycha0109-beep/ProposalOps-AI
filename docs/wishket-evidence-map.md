# Wishket Requirement → Repository Evidence Map

대상 공고: **제안서 작성 자동화를 위한 AI 프롬프트 엔지니어링**

이 문서는 공고 요구사항을 ProposalOps AI의 실제 구현 및 raw benchmark evidence와 연결합니다.

> 모든 benchmark/제안서/RFP는 synthetic/demo입니다.

| 공고 요구 | ProposalOps AI 구현 | 검증 증거 |
|---|---|---|
| 기존 PPT/PDF 제안서 데이터 자산화 | PPTX/PDF page extraction adapter + Proposal Asset schema/taxonomy/provenance | `scripts/extract_proposal_source.py`, `docs/proposal-source-extraction.md`, `data/taxonomy/` |
| RFP 분석 | requirement/deliverable/numeric/source quote 추출 | `reports/rfp-analyzer-dev-v1-gpt56luna.json`, `reports/rfp-analyzer-holdout-v1-gpt56luna.json` |
| 기존 제안서 검색 | 51 normal assets + 12 hard negatives | `evals/frozen/v1/*/retrieval.json`, `docs/retrieval-baseline.md` |
| Reference 반영 검증 | requirement별 Evidence Pack + allowed use | `evals/strategist/inputs-v1.json` |
| 제안 전략/컨셉 | requirement/evidence binding + information class separation | `reports/proposal-strategist-dev-v1-gpt56luna.json`, `reports/proposal-strategist-holdout-v1-gpt56luna.json` |
| 목차/페이지네이션 | requirement / strategy / evidence ID를 page에 연결 + deterministic coverage gate | `reports/dify-phase3-pagination-rfp-test-002.json`, `runs/e2e-demo/RFP-TEST-002/pagination-repaired-cycle-3.json` |
| 장표별 텍스트 초안 | claim_type + evidence IDs + client confirmation + deterministic provenance gate | `reports/dify-phase4-package-rfp-test-002.json`, `runs/e2e-demo/RFP-TEST-002/slides-repaired-cycle-3.json` |
| 이미지 생성용 프롬프트 | visual type, diagram spec, prohibited elements, fact risk + visual provenance gate | `reports/dify-phase4-package-rfp-test-002.json`, `runs/e2e-demo/RFP-TEST-002/visuals-repaired-cycle-3.json` |
| hallucination 최소화 | explicit QA taxonomy + semantic evidence validation | `reports/proposal-qa-dev-v1-gpt56luna.json`, `reports/proposal-qa-holdout-v1-gpt56luna.json` |
| 오류 자동 수정 | affected provenance chain만 targeted repair + bounded repair orchestration | `scripts/run_dify_phase4_package.py`, `runs/e2e-demo/RFP-TEST-002/repair-cycle-3.json` |
| Prompt Engineering 개선 증명 | v0~v4 raw runs, evaluator, acceptance, candidate freeze, holdout | `runs/`, `reports/`, `evals/frozen/v1/*-candidate.json` |
| 최종 통합 데모 | legacy E2E 8 pages + current Dify live package 6 pages / 6 slides / 6 visuals / final QA PASS | `reports/e2e-demo-summary.md`, `reports/dify-phase4-package-rfp-test-002.json` |
| agent 설정 가이드 | vendor-neutral blueprint + Dify DSL 0.7.0 Phase 2~4 import candidates | `dify/workflow-spec.yaml`, `dify/proposalops-phase4-package.yml`, `dify/phase4-import-guide.md` |

## RFP Analyzer

GPT-5.6 Luna / reasoning low / frozen dev benchmark:

| Version | Assertion | Numeric | Requirement | JSON | Schema | Grounding |
|---|---:|---:|---:|---:|---:|---:|
| v0 | 80.83% | 82.86% | 75% | 0% | 0% | 0% |
| v1 | 90.83% | 92.85% | 100% | 100% | 100% | 0% |
| v2 | 90.83% | 92.85% | 100% | 100% | 0% | 100% |
| v3 | 90.83% | 82.86% | 100% | 100% | 0% | 100% |
| **v4** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** |

v4 holdout도 모든 핵심 metric 100%, unsupported addition 0입니다.

## Proposal Strategist

v3:

- requirement/evidence coverage: 100%
- information class separation: 50%

v4:

- dev information class separation: 100%
- holdout information class separation: 100%
- evidence validity: 100%
- unsupported company/quantitative claims: 0
- invalid evidence references: 0

## Proposal QA

v3는 error detection은 가능했지만 executable prompt에 taxonomy enum이 빠져 error type accuracy가 0%였습니다.

v4 dev + holdout:

- BLOCK recall: 100%
- false positive rate: 0%
- error type accuracy: 100%
- severity accuracy: 100%

## E2E Hallucination Guardrail Evidence

최초 E2E는 8개 page/slide/visual을 생성했지만 QA가 reference 의미 범위를 초과한 문장을 BLOCK했습니다.

최종 cycle 3에서는:

```text
Strategy
→ Pagination
→ Slide
→ Visual
```

중 affected chain만 수정했고 final QA는:

```json
{
  "status": "PASS",
  "issues": []
}
```

상세: `reports/e2e-demo-summary.md`

## 현재 미구현 / account-bound 영역

완료된 Dify 범위:

- Dify Cloud Knowledge production/benchmark dataset 업로드
- frozen 48-query semantic retrieval 비교
- Phase 2 RFP → retrieval → evidence → strategy live PASS
- Phase 3 pagination + deterministic coverage gate live PASS
- Phase 4 slide → visual → QA final package live PASS
- Dify DSL 0.7.0 Phase 2~4 candidate + structural CI validation

남은 범위:

- 스캔/image-only PDF OCR 및 복잡한 layout/table/image reconstruction
- 사용자 Dify Studio authenticated session에서 실제 DSL import / node UI smoke test

따라서 이 포트폴리오는 **prompt engineering + evidence/provenance workflow + synthetic Dify live integration 검증**을 증명하며, 특정 고객사의 실제 운영성과를 주장하지 않습니다.

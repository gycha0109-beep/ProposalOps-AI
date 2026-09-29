# Wishket Requirement → Repository Evidence Map

대상 공고: **제안서 작성 자동화를 위한 AI 프롬프트 엔지니어링**

이 문서는 공고 요구사항을 ProposalOps AI 저장소의 재현 가능한 증거와 연결합니다.

| 공고 요구 | ProposalOps AI 구현 | 증거 |
|---|---|---|
| 기존 PPT/PDF 제안서 데이터 자산화 | Proposal Asset 단위 구조화, taxonomy, metadata | `data/processed/proposals/`, `data/taxonomy/` |
| RFP 분석 | requirement / deliverable / numeric extraction benchmark | `prompts/rfp_analyzer/`, `reports/rfp-analyzer-dev-v1-gemini36.*` |
| 기존 제안서 검색 | 63개 retrieval asset, hard negative 포함 | `evals/frozen/v1/*/retrieval.json`, `docs/retrieval-baseline.md` |
| Reference 반영 검증 | Evidence Pack + provenance chain | `prompts/production/evidence_builder.md`, `evals/strategist/inputs-v1.json` |
| 제안 전략/컨셉 | requirement/evidence bound strategist | `prompts/proposal_strategist/`, `scripts/run_strategy_benchmark.py` |
| 목차/페이지네이션 | requirement/page/strategy/evidence ID 연결 | `prompts/production/pagination.md` |
| 장표별 텍스트 초안 | claim type + evidence IDs + client confirmation | `prompts/production/slide_draft.md` |
| 이미지 생성용 프롬프트 | visual enum, chart fact guardrail | `prompts/production/visual_prompt.md` |
| hallucination 최소화 | unsupported claim / invalid reference / missing requirement QA | `evals/qa-injected-errors/`, `scripts/run_qa_benchmark.py` |
| 오류 자동 수정 | stage-targeted repair | `prompts/production/targeted_repair.md` |
| prompt engineering 개선 증명 | frozen dev/holdout, raw output, evaluator, acceptance gate | `evals/frozen/v1/`, `runs/`, `reports/` |
| agent 설정 가이드 | vendor-neutral workflow blueprint | `dify/workflow-spec.yaml`, `dify/setup-guide.md` |

## 현재 실제 측정된 RFP Analyzer 결과

Frozen dev / Gemini 3.6 Flash / evaluator 1.5:

| Version | Assertion | Numeric | Requirement | JSON | Canonical Schema | Quote Coverage |
|---|---:|---:|---:|---:|---:|---:|
| v0 | 66.66% | 72.86% | 33.33% | 0% | 0% | 0% |
| v1 | 95% | 100% | 100% | 100% | 100% | 0% |
| v2 | 95% | 100% | 100% | 100% | 0% | 100% |
| v3 | 95% | 90% | 100% | 50% | 0% | 50% |

해석:

- v1: structured output으로 정확도/구조 안정성 개선
- v2: grounding 100% 확보, 대신 schema drift 발생
- v3: 규칙 과밀로 JSON truncation 회귀 발생
- v4: 위 실패 원인을 반영한 compact grounded candidate, 현재 provider 503/429로 NOT_EVALUATED

최종 production 개선율은 v4 dev → freeze → holdout 전에는 주장하지 않습니다.

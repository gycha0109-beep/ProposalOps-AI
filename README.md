# ProposalOps AI

공공기관 RFP와 과거 제안서 자산을 이용해 **RFP 분석 → 근거 검색 → 제안 전략 → 페이지 구성 → 장표 초안 → 시각화 프롬프트 → QA/수정**까지 연결하는 AI 제안 자동화 PoC입니다.

핵심은 단순 생성이 아니라 **프롬프트 엔지니어링이 동일한 frozen benchmark에서 실제 품질을 개선했는지 raw output과 evaluator로 재현 가능하게 증명하는 것**입니다.

> 모든 제안서/RFP/성과 데이터는 synthetic/demo 데이터입니다. 실제 고객 수행 실적이나 생산성 개선 수치가 아닙니다.

## Final Status

세 핵심 prompt track은 모두 GPT-5.6 Luna / reasoning low 조건에서 **dev → candidate freeze → holdout**까지 완료했습니다.

| Track | Frozen candidate | Dev | Holdout |
|---|---|---|---|
| RFP Analyzer | `v4_compact_grounded` | PASS | PASS |
| Proposal Strategist | `v4_explicit_classes` | PASS | PASS |
| Proposal QA | `v4_compact_taxonomy` | PASS | PASS |

실제 E2E demo도 완료했습니다.

```text
RFP Analyzer
→ Evidence Pack
→ Proposal Strategist
→ Pagination
→ Slide Draft
→ Visual Prompt
→ Proposal QA
→ Provenance-chain Targeted Repair
→ Final Package PASS
```

RFP-TEST-002 데모 결과:

- pages: **8**
- slide drafts: **8**
- visual specifications: **8**
- initial final QA: **FAIL**
- final provenance-chain repair: **PASS**
- final QA issues: **0**

상세: `reports/e2e-demo-summary.md`

## Prompt Engineering Results

### RFP Analyzer

동일 GPT-5.6 Luna / reasoning low / frozen dev RFP 2종 조건입니다.

| Version | Assertion | Numeric | Requirement | JSON | Schema | Quote grounding |
|---|---:|---:|---:|---:|---:|---:|
| v0 | 80.83% | 82.86% | 75% | 0% | 0% | 0% |
| v1 | 90.83% | 92.85% | 100% | 100% | 100% | 0% |
| v2 | 90.83% | 92.85% | 100% | 100% | 0% | 100% |
| v3 | 90.83% | 82.86% | 100% | 100% | 0% | 100% |
| **v4** | **100%** | **100%** | **100%** | **100%** | **100%** | **100%** |

v4 holdout RFP-TEST-003:

- assertion pass: **100%**
- numeric fidelity: **100%**
- requirement recall: **100%**
- source quote coverage/validity: **100% / 100%**
- canonical schema validity: **100%**
- unsupported additions: **0**

### Proposal Strategist

v3는 requirement/evidence grounding 자체는 통과했지만 information-class separation이 50%였습니다.

v4에서 `RFP_FACT / REFERENCE_FACT / REFERENCE_PATTERN / AI_RECOMMENDATION`을 명시적으로 분리했습니다.

v4 dev + holdout:

- result coverage: **100%**
- requirement coverage: **100%**
- evidence citation coverage: **100%**
- evidence validity: **100%**
- information class separation: **100%**
- unsupported company claims: **0**
- unsupported quantitative claims: **0**
- invalid evidence references: **0**

### Proposal QA

v3는 오류 자체는 탐지했지만 executable prompt에 taxonomy enum이 빠져 error-type accuracy가 0%였습니다.

v4에서 7개 error taxonomy와 severity contract를 명시했습니다.

v4 dev + holdout:

- BLOCK recall: **100%**
- false positive rate: **0%**
- error type accuracy: **100%**
- severity accuracy: **100%**

## E2E Grounding / Repair Result

첫 E2E package는 8개 page/slide/visual을 생성했지만 final QA가 `INVALID_REFERENCE`를 BLOCK했습니다.

단순 ID 오류가 아니라 evidence가 지원하는 의미 범위보다 다음 문구가 과하게 확장된 문제였습니다.

- PAGE-006: 게시 전 확인 근거를 “제작 시점 확인 / 공식 담당자·채널”까지 확장
- PAGE-008: evidence에 없는 “시청 단계 / 세부 분석 축” 추가

두 번의 downstream-only repair 후에도 upstream Strategy/Pagination에 원인이 남아 있음을 QA가 재탐지했습니다.

Cycle 3에서는 다음 provenance chain만 수정했습니다.

```text
ST-05 / ST-06
→ PAGE-006 / PAGE-008
→ Slide
→ Visual
```

나머지 6개 page chain은 재생성하지 않았습니다.

최종 QA:

```json
{
  "status": "PASS",
  "issues": []
}
```

Evidence:

- `runs/e2e-demo/RFP-TEST-002/final-package-repaired.json`
- `runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-3.json`
- `runs/e2e-demo/RFP-TEST-002/repair-cycle-3.json`

## Retrieval Baseline v1

문자 n-gram TF-IDF lexical baseline입니다.

| Split | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| dev (32) | 90.62% | 100% | 100% | 0.9531 |
| holdout (16) | 93.75% | 100% | 100% | 0.9688 |

- normal proposal assets: 51
- hard negatives: 12
- total retrieval assets: 63

이 수치는 Dify Knowledge나 embedding/reranker 성능이 아니라 로컬 lexical baseline입니다.

상세: `docs/retrieval-baseline.md`

## Evaluation Integrity

```text
Synthetic data
→ Gold assertions 작성
→ Benchmark v1 freeze
→ Dev 실행
→ Acceptance criteria 판정
→ Candidate prompt/hash freeze
→ Holdout 1회
→ Raw output + evaluator result 보존
```

- dev RFP: `RFP-TEST-001`, `RFP-TEST-002`
- holdout RFP: `RFP-TEST-003`
- benchmark manifest: `evals/frozen/v1/manifest.json`
- frozen candidate state: `evals/frozen/v1/*-candidate.json`

holdout을 본 뒤 같은 v1 candidate를 다시 튜닝하지 않습니다.

## Production / Demo Status

Frozen benchmark prompts:

- `prompts/production/rfp_analyzer.md`
- `prompts/production/proposal_strategist.md`
- `prompts/production/proposal_qa.md`

E2E demo-validated, dedicated benchmark는 아직 없는 integration prompts:

- `prompts/production/pagination.md`
- `prompts/production/slide_draft.md`
- `prompts/production/visual_prompt.md`
- `prompts/production/targeted_repair.md`

Logical agent blueprint:

- `dify/workflow-spec.yaml`
- `dify/setup-guide.md`

> `workflow-spec.yaml`은 특정 제품의 import 가능한 DSL이 아니라 Dify/Antigravity 등에 구현하기 위한 vendor-neutral logical blueprint입니다.

## Portfolio Navigation

- Wishket 요구사항 ↔ 저장소 증거: `docs/wishket-evidence-map.md`
- 3분 데모 가이드: `docs/demo-guide.md`
- 통합 benchmark scorecard: `reports/benchmark-scorecard.md`
- E2E 최종 8페이지 package 요약: `reports/e2e-demo-final-package.md`
- E2E 결과/repair story: `reports/e2e-demo-summary.md`
- RFP failure analysis: `docs/prompt-failure-analysis/rfp-analyzer-dev-v1.md`
- RFP benchmark guide: `docs/rfp-analyzer-benchmark-runner.md`
- QA benchmark guide: `docs/proposal-qa-benchmark-runner.md`
- Strategist benchmark guide: `docs/proposal-strategist-benchmark-runner.md`

## Repository Structure

```text
ProposalOps-AI/
├─ .github/workflows/
├─ configs/
├─ data/
├─ dify/
├─ docs/
├─ evals/
│  └─ frozen/v1/
├─ prompts/
│  ├─ rfp_analyzer/
│  ├─ proposal_strategist/
│  ├─ proposal_qa/
│  └─ production/
├─ reports/
├─ runs/
│  ├─ rfp_analyzer/
│  ├─ proposal_qa/
│  ├─ proposal_strategist/
│  └─ e2e-demo/
└─ scripts/
```

## Dify Knowledge Integration

### Phase 1 — Knowledge / Retrieval

실제 Dify Cloud Sandbox 연결과 Knowledge retrieval benchmark를 완료했습니다.

- production corpus: **51** normal Proposal Assets
- benchmark corpus: **63** = 51 normal + 12 hard negatives
- High Quality semantic retrieval: **48 frozen queries complete**
- DEV Hit@1: **90.62%**
- HOLDOUT Hit@1: **93.75%**
- Hit@3 / Hit@5: **100% / 100%**
- local char n-gram TF-IDF baseline과 aggregate metric 동률

Evidence:

- `reports/dify-retrieval-v1-semantic.json`
- `docs/dify-knowledge-phase1.md`

### Phase 2 — Grounded Strategy Core

RFP-TEST-002를 실제 live chain으로 실행했습니다.

```text
RFP Analyzer
→ dual-query Retrieval Planner
→ Dify Production Knowledge semantic retrieval
→ Evidence Builder
→ Proposal Strategist
```

Final validation:

- RFP requirement IDs: **PASS**
- Retrieval Planner contract: **PASS**
- Evidence primary recall / precision / provenance / status: **100%**
- unsupported company / numeric claims: **0 / 0**
- Strategist requirement coverage / evidence citation / evidence validity: **100%**
- information-class separation: **100%**
- broken provenance chain: **0**
- Phase 2 Core: **PASS**

Evidence:

- `reports/dify-phase2-core-rfp-test-002.json`
- `reports/dify-phase2-core-rfp-test-002.md`
- `docs/dify-phase2-core.md`
- `dify/proposalops-phase2-core.yml` — current Dify DSL **0.7.0** Studio import candidate
- `dify/phase2-import-guide.md` — Studio import / smoke-test checklist
- `scripts/validate_dify_phase2_dsl.py` — DSL structure / dataset / rate-limit / secret-leak gate

Evidence Builder도 별도 live benchmark에서 frozen candidate `v1_grounded`가 PASS했습니다.

### Phase 3 — Pagination + Coverage Gate

Phase 2의 grounded strategy를 실제 페이지 구조로 변환하는 downstream stage도 live 실행했습니다.

```text
Proposal Strategist
→ Pagination Planner
→ deterministic Coverage Validator
```

RFP-TEST-002:

- generated pages: **6**
- page limit: **8**
- requirements covered: **6 / 6**
- blocking errors: **0**
- warnings: **0**
- invalid requirement / strategy / evidence references: **0**
- Phase 3: **PASS**

Coverage Validator는 canonical structured IDs를 검사하므로 LLM judge가 아니라 deterministic code gate로 구현했습니다.

Evidence:

- `reports/dify-phase3-pagination-rfp-test-002.json`
- `reports/dify-phase3-pagination-rfp-test-002.md`
- `docs/dify-phase3-pagination.md`

Dify Studio candidate:

- Phase 2: `dify/proposalops-phase2-core.yml` — 14 nodes / 12 edges
- Phase 3: `dify/proposalops-phase3-pagination.yml` — 16 nodes / 14 edges

둘 다 current Dify DSL version `0.7.0` 기준으로 정적 CI 검증합니다.
실제 사용자의 Studio import/smoke test는 Account OAuth/console session이 필요한 별도 단계이므로
Service API key만으로 완료했다고 주장하지 않습니다.

## Remaining Work

완료:

- [x] synthetic Proposal Asset corpus
- [x] frozen dev/holdout benchmark
- [x] hard-negative retrieval baseline
- [x] RFP Analyzer dev + holdout
- [x] Proposal Strategist dev + holdout
- [x] Proposal QA dev + holdout
- [x] Evidence Builder live dev benchmark + frozen candidate
- [x] frozen production prompt promotion
- [x] Pagination / Slide / Visual live E2E
- [x] final QA BLOCK evidence
- [x] provenance-chain targeted repair
- [x] final E2E QA PASS
- [x] GitHub Actions reproducibility / candidate-state validation
- [x] vendor-neutral agent workflow blueprint
- [x] Dify production Knowledge upload
- [x] Dify benchmark Knowledge upload
- [x] Dify frozen semantic retrieval 48-query comparison
- [x] Dify Phase 2 RFP → Retrieval → Evidence → Strategy live PASS

남음:

- [x] current Dify DSL 0.7.0 import candidate + structural CI validation
- [ ] Dify Studio node UI import / smoke test
- [x] Strategy → Pagination → deterministic Coverage Validator live PASS + Dify DSL wiring
- [ ] Pagination → Slide Draft → Visual Prompt node wiring
- [ ] Proposal QA / targeted repair node wiring
- [ ] 실제 고객 제공 PPT/PDF를 사용할 경우 extraction adapter 교체

현재 포트폴리오에서 주장하는 성능은 **synthetic frozen benchmark와 demo/live workflow 결과에 한정**합니다.

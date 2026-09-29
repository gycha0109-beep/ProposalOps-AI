# Prompt Engineering Case Study

## Question

이 프로젝트의 질문은 “AI가 제안서를 쓸 수 있는가?”가 아닙니다.

**같은 frozen input과 같은 모델을 사용할 때 prompt contract를 개선하면 구조 안정성, grounding, 오류 탐지가 실제로 개선되는가?**

모든 실험 데이터는 synthetic/demo입니다.

Fixed live model:

- OpenAI Responses API
- `gpt-5.6-luna`
- reasoning effort `low`

## Track A — RFP Analyzer

### Baseline

v0:

- assertion: 80.83%
- numeric fidelity: 82.86%
- requirement recall: 75%
- JSON parseable: 0%

### Engineering path

v1 — structured schema:
- requirement recall 100%
- canonical schema 100%
- grounding 없음

v2 — source grounding:
- source quote coverage/validity 100%
- canonical schema 0%로 regression

v3 — 더 많은 guardrail:
- grounding은 유지
- numeric fidelity가 82.86%로 regression
- schema 문제도 해결되지 않음

v4 — compact grounded contract:
- fixed top-level schema
- explicit unknown
- number preservation
- minimal source quote
- key rename 금지

### Result

Dev:

- assertion 100%
- numeric 100%
- requirement 100%
- JSON 100%
- schema 100%
- grounding 100%
- unsupported addition 0

Holdout:

동일 핵심 지표 100%, unsupported addition 0.

Evidence:

- `reports/rfp-analyzer-dev-v1-gpt56luna.json`
- `reports/rfp-analyzer-holdout-v1-gpt56luna.json`

## Track B — Proposal Strategist

### Baseline problem

과거 제안서 pattern과 신규 아이디어를 명확히 분리하지 않으면 reference가 회사 사실처럼 승격될 위험이 있습니다.

v3는:

- requirement coverage 100%
- evidence validity 100%
- unsupported claims 0

이었지만 information-class separation이 **50%**였습니다.

### v4 intervention

Output contract에 다음을 명시했습니다.

- RFP_FACT
- REFERENCE_FACT
- REFERENCE_PATTERN
- AI_RECOMMENDATION

그리고 evidence가 없는 신규 전략은 AI_RECOMMENDATION으로 분리하도록 강제했습니다.

### Result

v4 dev + holdout:

- requirement coverage 100%
- evidence citation 100%
- evidence validity 100%
- information class separation 100%
- unsupported company claims 0
- unsupported quantitative claims 0
- invalid evidence references 0

Evidence:

- `reports/proposal-strategist-dev-v1-gpt56luna.json`
- `reports/proposal-strategist-holdout-v1-gpt56luna.json`

## Track C — Proposal QA

### v3 failure

v3는 오류 탐지 자체는 가능했지만 실행 prompt에 explicit taxonomy enum이 빠져 error-type accuracy가 **0%**였습니다.

### v4 intervention

허용 error type과 severity를 고정했습니다.

Error types:

- MISSING_REQUIREMENT
- UNSUPPORTED_CLAIM
- INVALID_REFERENCE
- CROSS_PROPOSAL_MERGE
- STRATEGY_PAGE_MISMATCH
- DUPLICATE_MESSAGE
- OVERLONG_SLIDE

Severity:

- BLOCK
- WARN
- INFO

### Result

v4 dev + holdout:

- BLOCK recall 100%
- false positive 0%
- error type accuracy 100%
- severity accuracy 100%

Evidence:

- `reports/proposal-qa-dev-v1-gpt56luna.json`
- `reports/proposal-qa-holdout-v1-gpt56luna.json`

## E2E — Why provenance matters

RFP-TEST-002로 실제 package를 생성했습니다.

- 8 pages
- 8 slide drafts
- 8 visual specifications

최초 final QA는 FAIL했습니다.

문제는 invalid ID가 아니라 **reference의 의미 범위를 초과한 주장**이었습니다.

예:

```text
Evidence:
게시 전 변경정보 확인

Generated claim:
제작 시점 + 게시 직전 확인
```

ID 자체는 유효하지만 evidence가 claim 전체를 지원하지 않습니다.

### Repair cycle 1 / 2

downstream slide/visual만 고쳐도 upstream strategy와 pagination에 과잉 표현이 남아 re-QA가 다시 BLOCK했습니다.

또한 PAGE-008의 KPI chain에 evidence가 없는 `시청` 단계와 분석 축이 추가된 것도 발견했습니다.

### Repair cycle 3

수정 범위를 provenance chain까지 확장했습니다.

```text
ST-05 / ST-06
→ PAGE-006 / PAGE-008
→ Slide
→ Visual
```

affected chain만 수정하고 다른 6개 page chain은 유지했습니다.

Final QA:

```json
{
  "status": "PASS",
  "issues": []
}
```

Evidence:

- `reports/e2e-demo-summary.md`
- `runs/e2e-demo/RFP-TEST-002/repair-cycle-3.json`
- `runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-3.json`

## What the portfolio proves

단순히 “좋은 prompt를 만들었다”가 아니라 다음 과정을 raw evidence로 보존합니다.

```text
baseline failure
→ intervention
→ regression
→ failure analysis
→ candidate redesign
→ frozen dev acceptance
→ prompt/hash freeze
→ untouched holdout
→ production promotion
→ E2E QA
→ provenance-chain repair
```

각 track에서 다음을 공개합니다.

- input
- prompt variants
- raw model output
- frozen gold
- evaluator
- acceptance report
- candidate SHA/hash
- holdout output
- failure examples
- final production prompt

결과 숫자 자체보다 **어떻게 측정했고 왜 수정했으며 다시 실행 가능한지**를 핵심 증거로 사용합니다.

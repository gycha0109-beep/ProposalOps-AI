# E2E Demo Result — RFP-TEST-002

> Synthetic/demo benchmark. 실제 고객 제안서나 고객 성과가 아닙니다.

## Final status

- provider: OpenAI Responses API
- model: `gpt-5.6-luna`
- reasoning effort: `low`
- RFP: `RFP-TEST-002`
- final package status: **PASS**
- final QA issues: **0**
- pages: **8**
- slides: **8**
- visual specifications: **8**

Final package:

`runs/e2e-demo/RFP-TEST-002/final-package-repaired.json`

Final QA:

`runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-3.json`

## Reused validated stages

E2E 데모는 이미 frozen benchmark를 통과한 결과를 재사용했습니다.

- RFP Analyzer v4: `runs/rfp_analyzer/benchmark-v1-gpt56luna/dev/v4_compact_grounded/RFP-TEST-002/run-01.json`
- Proposal Strategist v4: `runs/proposal_strategist/benchmark-v1-gpt56luna/dev/v4_explicit_classes/run-01.json`
- Evidence Pack: `evals/strategist/inputs-v1.json`

새로 생성한 단계:

```text
Pagination
→ Slide Draft batch
→ Visual Prompt batch
→ Proposal QA
```

## First generation

첫 E2E 생성은 구조적으로 정상 완료됐습니다.

- Pagination: 8 pages
- Slide Draft: 8 slides
- Visual Prompt: 8 specifications
- mandatory RFP requirements R-201~R-206: all covered

그러나 최종 Proposal QA는 **FAIL**했습니다.

### Initial QA BLOCK

`PAGE-006`에서 다음 운영 방식이 reference evidence 범위를 초과했습니다.

> 공식 확인 채널 및 담당자를 통해 정보를 재확인

EV-R-205-01 / EV-R-205-02는 게시 전 변경정보 확인, 재검수, 상태 갱신은 지원하지만 이미 정의된 공식 담당자·채널 운영 방식까지 지원하지 않았습니다.

원본:

- `runs/e2e-demo/RFP-TEST-002/qa.json`
- `runs/e2e-demo/RFP-TEST-002/final-package.json`

## Repair cycle 1

PAGE-006 slide/visual만 수정했습니다.

결과: **FAIL**

QA가 남은 표현을 다시 차단했습니다.

- `제작 시점과 게시 직전에 재확인`
- evidence는 게시 전 확인을 지원하지만 제작 시점 확인까지 직접 지원하지 않음

Evidence:

- `repair.json`
- `qa-recheck.json`

## Repair cycle 2

REFERENCE_PATTERN 문장을 evidence가 직접 entail하는 범위로 더 축소했습니다.

결과: **FAIL**

이 단계에서 QA가 downstream 문장뿐 아니라 **upstream provenance chain**의 문제를 발견했습니다.

### PAGE-006

- ST-05와 Pagination에 아직 `제작 시점` 표현이 남아 있었음

### PAGE-008

- `시청` KPI 단계
- `콘텐츠 유형·방문 동기·크리에이터별 전환 비교`

가 EV-R-206-01 / EV-R-206-02의 직접 지원 범위를 초과했습니다.

Evidence:

- `repair-cycle-2.json`
- `qa-recheck-cycle-2.json`

## Repair cycle 3 — provenance-chain repair

수정 범위를 정확히 상류까지 확장했습니다.

수정된 strategy:

- ST-05
- ST-06

수정된 pages:

- PAGE-006
- PAGE-008

수정된 stage:

```text
Strategy
→ Pagination
→ Slide
→ Visual
```

나머지 strategy/page chain은 재생성하지 않았습니다.

### ST-05 / PAGE-006

근거가 직접 지원하는 범위로 제한:

- 게시 전 변경정보 확인
- 변경 시 기존 게시물/연결 콘텐츠 상태 갱신
- 버전 표시

제거:

- 제작 시점 확인
- 이미 확정된 공식 담당자/채널 workflow

### ST-06 / PAGE-008

근거가 직접 지원하는 KPI로 제한:

```text
도달
→ 상세조회
→ 저장
→ 지도·코스·예약 페이지 이동
```

제거:

- 시청 단계
- 콘텐츠 유형·방문 동기·크리에이터별 분석 축

## Final QA

Cycle 3 re-QA:

```json
{
  "status": "PASS",
  "issues": []
}
```

QA summary:

> 제공된 RFP 요구사항은 모두 페이지에 반영되어 있으며, 회사 실적·정량 성과의 무근거 주장이나 유효하지 않은 evidence 연결이 확인되지 않았습니다.

Evidence:

- `runs/e2e-demo/RFP-TEST-002/repair-cycle-3.json`
- `runs/e2e-demo/RFP-TEST-002/qa-recheck-cycle-3.json`
- `runs/e2e-demo/RFP-TEST-002/final-package-repaired.json`

## What this demonstrates

이 데모의 핵심은 최초 생성 결과가 한 번에 완벽했다는 것이 아닙니다.

```text
RFP requirement
→ Evidence
→ Strategy
→ Page
→ Slide
→ Visual
→ QA
```

의 provenance chain을 유지했기 때문에 QA가 단순한 잘못된 ID뿐 아니라 **reference의 의미 범위를 초과한 주장**을 탐지했고, 전체 proposal을 다시 생성하지 않고 affected chain만 수정할 수 있었습니다.

이는 다음을 실제 raw evidence로 보여줍니다.

- requirement coverage
- evidence-bound generation
- unsupported claim detection
- semantic reference validation
- targeted repair
- upstream provenance repair
- final QA pass

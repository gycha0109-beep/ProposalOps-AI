# Dify Phase 4 — Slide / Visual / QA / Repair

## Goal

Phase 3에서 PASS한 Pagination을 실제 제안서 slide draft와 visual specification으로 확장하고,
구조 검증과 semantic QA를 모두 통과한 final package를 만든다.

```text
Pagination PASS
→ Slide Draft
→ Slide Provenance Gate
→ Visual Prompt
→ Visual Provenance Gate
→ Proposal QA
→ targeted repair if needed
→ Final Package
```

모든 benchmark/live evidence는 synthetic/demo 데이터다.

## Authoritative implementation

Python orchestration:

- `scripts/run_dify_phase4_package.py`
- `configs/dify-phase4-package-v1.json`

Deterministic gates:

- `scripts/lib/slide_eval.py`
- `scripts/lib/visual_eval.py`
- `scripts/lib/repair_router.py`

CI:

- `.github/workflows/dify-phase4-package.yml`

## Final live result

RFP:

`RFP-TEST-002`

Source:

- Phase 2: `reports/dify-phase2-core-rfp-test-002.json`
- Phase 3: `reports/dify-phase3-pagination-rfp-test-002.json`

Model:

`gpt-5.6-luna` / reasoning low

Final successful run:

- pages: **6**
- slides: **6**
- visuals: **6**
- Coverage Gate: **PASS**
- Slide Provenance Gate: **PASS**
- Visual Provenance Gate: **PASS**
- Proposal QA: **PASS**
- QA issues: **0**
- broken provenance chains: **0**
- repair cycles: **0**
- final status: **PASS**

The successful final run used the normal three-call path:

1. Slide Draft batch
2. Visual Prompt batch
3. Proposal QA

No repair call was required after the generation contracts were tightened.

## Provenance

```text
R-201 → PA-PR-007-P015 → EV-R-201-01 → ST-01 → PAGE-001
R-202 → PA-PR-007-P016 → EV-R-202-01 → ST-02 → PAGE-002
R-203 → PA-VIDEO-004-P021 → EV-R-203-01 → ST-03 → PAGE-003
R-204 → PA-PR-007-P018 → EV-R-204-01 → ST-04 → PAGE-004
R-205 → PA-CAMP-010-P023 → EV-R-205-01 → ST-05 → PAGE-005
R-206 → PA-CAMP-010-P024 → EV-R-206-01 → ST-06 → PAGE-006
```

## Why deterministic gates exist before QA

Structural failures do not need an LLM judge.

Slide Gate blocks:

- missing/duplicate page linkage
- invalid evidence IDs
- evidence from another requirement/page
- REFERENCE_FACT / REFERENCE_PATTERN without evidence
- RFP_FACT / AI_RECOMMENDATION with reference evidence
- slide/body evidence summary mismatch
- invalid claim/visual enums

Visual Gate blocks:

- visual/slide type mismatch
- evidence outside the validated slide
- invalid process diagrams
- reference-image use without a validated asset channel
- data_chart without quantitative slide input
- quantitative values absent from the validated slide/page

Proposal QA remains the semantic judge for:

- unsupported claim
- invalid semantic reference
- cross-proposal merge
- requirement/strategy mismatch
- duplicate message
- overlong slide

## Failure analysis that changed the design

Intermediate Phase 4 runs exposed two validator/design issues.

### Visual numeric false positives

The first gate counted technical node IDs such as `n1` and `n2` as invented numbers.
The numeric check was restricted to user-visible visual content.

A later run also showed that valid RFP deliverable quantities from Pagination could appear in a visual
even when the Slide body did not repeat them. The allowed numeric source was therefore changed to:

```text
validated Slide + corresponding Pagination page
```

### Evidence scope drift

An intermediate QA run caught PAGE-003 wording that exceeded `EV-R-203-01`.

The evidence directly supports:

- Hook → Core → Action
- one action goal per video

It does not automatically support arbitrary concrete action examples or broader creative claims.

Phase 4 generation now follows:

```text
Evidence scope > broader upstream strategy/page wording
```

If upstream wording is broader than the cited evidence, the Slide must narrow the wording rather than copy it.

## Repair policy

Python authoritative runner:

- maximum repair cycles: **3**
- each cycle repairs only routed strategy/page IDs
- after repair: Coverage Gate → Slide Gate → Visual Gate → QA recheck
- unresolved BLOCK after the bound → `ESCALATION_REQUIRED`

The bound prevents unlimited model-call loops.

Intermediate validation runs did exercise targeted repair and confirmed page/strategy-scoped merge behavior.
The final successful run required **0 repairs**.

## Evidence

- `reports/dify-phase4-package-rfp-test-002.json`
- `reports/dify-phase4-package-rfp-test-002.md`
- `runs/dify/phase4/RFP-TEST-002/final-package.json`

## Dify Studio candidate

`dify/proposalops-phase4-package.yml`

Static structure:

- DSL: **0.7.0**
- nodes: **35**
- edges: **35**
- LLM nodes: **10**
- Code nodes: **12**
- If/Else nodes: **5**
- End nodes: **4**
- Production Knowledge node: **1**

The Studio DSL includes:

- normal QA PASS → Final Package
- deterministic gate failure → Gate Failure
- QA FAIL → Repair Router → Targeted Repair → merge gate → one QA recheck
- repaired PASS → Repaired Final Package
- unresolved failure → Escalation Required

The portable Studio candidate intentionally unrolls **one** repair/recheck pass.
The Python runner remains authoritative for the maximum three-cycle bounded repair policy.

The current Phase 4 Studio candidate also pins all ten LLM nodes to
`langgenius/openai/openai / gpt-5.6-luna` and uses globally unique End-output
variable names across the normal, gate-failure, repaired, and escalation branches.

Actual Studio import / node-UI smoke testing still requires the user's authenticated Dify Studio session
and is not claimed complete from Service API execution alone.

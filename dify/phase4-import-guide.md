# Dify Phase 4 Studio Import Guide

## Artifact

Import:

`dify/proposalops-phase4-package.yml`

Pre-import validation:

```bash
python scripts/validate_dify_phase4_dsl.py
```

Expected static result:

- Dify DSL: 0.7.0
- nodes: 35
- edges: 35
- production Knowledge dataset only
- embedded secrets: 0

## Graph

```text
RFP Analyzer
→ Retrieval Planner
→ Dify Production Knowledge
→ Evidence Builder
→ Proposal Strategist
→ Pagination Planner
→ Coverage Validator
→ Slide Draft
→ Slide Provenance Gate
→ Visual Prompt
→ Visual Provenance Gate
→ Proposal QA
      ├─ PASS → Final Package
      └─ FAIL → Repair Router
                  → Targeted Repair
                  → Merge + Repair Gate
                  → QA Recheck
                        ├─ PASS → Repaired Final Package
                        └─ FAIL → Escalation Required
```

Gate failures before QA terminate through `Gate Failure`.

## Model binding

The current Phase 4 DSL pins the ten LLM nodes to the configured OpenAI provider:

- provider: `langgenius/openai/openai`
- model: `gpt-5.6-luna`
- mode: `chat`

The import still depends on that provider/model being available in the target workspace.

Embedding used by the Knowledge dataset remains:

- `text-embedding-3-small`

## Knowledge binding

Production dataset:

`21dcb1f3-270f-4991-bcf8-b2782e6cf814`

Name:

`ProposalOps Production v1`

Do not connect the frozen benchmark dataset to the production workflow.

## Smoke input

Use:

`data/raw/rfps/RFP-TEST-002.md`

## Expected normal-path output

The validated live reference result is:

- 6 requirements
- 6 pages
- 6 slides
- 6 visuals
- Coverage PASS
- Slide Gate PASS
- Visual Gate PASS
- Proposal QA PASS / issues 0
- broken provenance chains 0
- repair cycles 0

Reference:

`reports/dify-phase4-package-rfp-test-002.json`

## Studio smoke PASS conditions

1. DSL imports without a blocking schema error.
2. All ten LLM nodes resolve to a workspace model.
3. Production Knowledge remains connected.
4. Query iteration remains serial.
5. RFP-TEST-002 reaches `Final Package` on the normal path.
6. Coverage, Slide, and Visual gates all report PASS.
7. Proposal QA reports PASS / issues 0.
8. Six page IDs produce six slide and visual objects.
9. No benchmark hard-negative asset is used.
10. No unsupported company achievement or quantitative result is introduced.

## Repair-branch smoke

A repair branch exists in the Studio candidate, but the latest validated RFP-TEST-002 normal run does not require it.

The Studio graph unrolls one repair/recheck pass for portability.
The authoritative Python runner supports up to three bounded repair cycles before escalation.


## Capture the Studio execution result

After the smoke run, keep the workflow execution JSON or copy the final `outputs` object.

The repository contains a validator that accepts either:

- the full Dify workflow execution response with `data.outputs`
- an object with `outputs`
- the outputs object itself

Validation command:

```bash
python scripts/validate_dify_studio_smoke.py studio-run.json --expect-pages 6
```

The validator re-runs the repository's deterministic:

- Pagination Coverage Gate
- Slide Provenance Gate
- Visual Provenance Gate
- final QA status / issue count
- requirement → evidence → strategy → page provenance linkage

Expected result:

```json
{
  "status": "PASS",
  "errors": [],
  "summary": {
    "pages": 6,
    "slides": 6,
    "visuals": 6,
    "qa_status": "PASS",
    "qa_issues": 0,
    "coverage_gate": "PASS",
    "slide_gate": "PASS",
    "visual_gate": "PASS",
    "broken_provenance_chains": 0
  }
}
```

This means the user-side Studio smoke does not rely only on visually inspecting green nodes.


## Dify checklist compatibility

Dify currently validates End-node output variable names globally across branches.
The Phase 4 DSL therefore keeps normal-path output names unchanged and prefixes non-normal branches:

- `gate_failure_*`
- `repaired_*`
- `escalation_*`

This avoids duplicate-output checklist errors after import.

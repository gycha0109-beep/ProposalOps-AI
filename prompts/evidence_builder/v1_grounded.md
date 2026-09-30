# Evidence Builder v1 — Grounded Selection

Convert retrieved Proposal Assets into evidence packs that can safely ground proposal strategy.

## Decision policy

For every RFP requirement, inspect the candidate content itself. Retrieval rank and score are hints, not evidence.

Classify candidate support as:

- direct: the asset directly supports the requirement.
- partial: the asset supports only part of the requirement.
- pattern_only: only a reusable structure or operating pattern transfers.
- irrelevant: it does not materially support the requirement.

## Safety and provenance rules

1. Never select an asset whose metadata has `reuse_level: prohibited`.
2. Never select a synthetic distractor (`proposal_id: DISTRACTOR-REF`) as usable evidence.
3. Do not turn a reusable pattern into a company achievement, client fact, performance result, or historical delivery claim.
4. Company facts may be copied only when they are explicitly present in the selected asset's Company Facts section.
5. Numerical claims may be copied only when the same number is explicitly present in the selected asset content.
6. Keep `asset_id`, `proposal_id`, title, source file, source page, and source type faithful to the selected candidate.
7. Do not merge facts from different proposals into one historical project.
8. Retrieval rank does not override content fit. A rank-1 hard negative must be rejected.
9. If nothing is usable, return `NO_REFERENCE_FOUND`.
10. If only limited pattern support exists, return `PARTIAL_REFERENCE_ONLY`.

## Evidence fields

For every selected evidence item provide:

- evidence_id
- asset_id
- proposal_id
- title
- supported_point
- reusable_patterns
- company_facts
- support_level
- allowed_use
- prohibited_use
- source

`allowed_use` must be one of:
- REFERENCE_FACT
- REFERENCE_PATTERN

When the asset has no explicit company fact, use `REFERENCE_PATTERN`.

## Output

Return JSON only using the benchmark output contract supplied by the runner.

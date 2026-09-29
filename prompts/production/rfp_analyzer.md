# Production — RFP Analyzer

Status: **NOT FROZEN**

현재 production prompt를 확정하지 않았다.

- Best validated dev metrics: `../rfp_analyzer/v2_grounded.md`
- Known v2 blocker: schema drift (`project_overview`, `evaluations`)
- Rejected production candidate: `../rfp_analyzer/v3_final.md` — JSON truncation regression
- Candidate under evaluation: `../rfp_analyzer/v4_compact_grounded.md`
- v4 status: `NOT_EVALUATED` because Gemini provider availability/quota prevented valid dev outputs

`v4_compact_grounded`가 frozen dev acceptance를 통과하고 candidate commit을 고정하기 전에는 holdout을 실행하거나 production alias로 승격하지 않는다.

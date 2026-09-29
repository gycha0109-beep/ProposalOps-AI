# Prompt Architecture

프롬프트는 실험 variants와 production 영역을 분리해 관리합니다.

## Experimental Tracks

- `rfp_analyzer/`: 요구사항 추출·구조 안정성·source grounding
- `proposal_strategist/`: 근거 기반 전략
- `proposal_qa/`: 오류 탐지

RFP Analyzer progression:

`v0_baseline → v1_structured → v2_grounded → v3_final → v4_compact_grounded`

이 버전들은 과거 고객 운영 이력을 의미하지 않고, frozen benchmark에서 intervention 효과를 비교하기 위한 실험 variants입니다.

현재 RFP Analyzer dev 결과:
- v1: 안정적인 JSON schema, grounding 없음
- v2: 95% assertion / 100% numeric / 100% requirement / 100% quote coverage & validity, 단 schema drift 관찰
- v3: JSON truncation regression
- v4: candidate 설계 완료, provider 503/429로 아직 NOT_EVALUATED

## Production

- RFP Analyzer: **NOT FROZEN**
- Proposal Strategist: `proposal_strategist/v3_final.md` candidate
- Proposal QA: `proposal_qa/v3_final.md` candidate

RFP Analyzer는 v4 dev acceptance 전까지 production alias를 확정하지 않습니다.

지원 prompt:
- Retrieval Planner
- Evidence Builder

평가 규칙: `../docs/evaluation-methodology.md`

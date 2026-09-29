# Prompt Architecture

프롬프트는 두 종류로 관리합니다.

## Experimental Tracks

프롬프트 엔지니어링 효과를 비교하기 위한 사전 정의 variants입니다. **과거 운영 이력을 의미하지 않습니다.**

- `rfp_analyzer/`: 요구사항 추출 품질
- `proposal_strategist/`: 근거 기반 전략 품질
- `proposal_qa/`: 오류 탐지 품질

RFP Analyzer는 dev 회귀 분석 이후 `v4_compact_grounded` candidate까지 확장했습니다. 다른 track은 아직 v0~v3 비교 구조입니다.

세부 intervention은 `experiment-manifest.json`에 기록합니다.

## Production

`production/`에는 실제 ProposalOps workflow에서 사용할 candidate prompt와 지원 prompt를 둡니다.

현재 production candidate:
- RFP Analyzer → `rfp_analyzer/v3_final.md` (v4 dev acceptance 전까지 유지)
- Proposal Strategist → `proposal_strategist/v3_final.md`
- Proposal QA → `proposal_qa/v3_final.md`

지원 prompt:
- Retrieval Planner
- Evidence Builder

## Evaluation Integrity

동일 frozen benchmark를 모든 버전에 적용하기 전에는 개선 수치를 주장하지 않습니다.

평가 규칙:
`../docs/evaluation-methodology.md`

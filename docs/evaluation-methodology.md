# Evaluation Methodology v1

## Purpose

ProposalOps AI의 프롬프트 엔지니어링 효과를 재현 가능하게 검증하기 위한 실험 규칙이다.

데이터는 synthetic/demo이며 실제 고객 프로젝트 성과가 아니다. 프롬프트 버전은 과거 운영 이력을 꾸민 것이 아니라 **비교 실험을 위해 사전 정의한 variants**다.

## Frozen Benchmark

Benchmark v1은 2026-09-29에 freeze했다.

- proposals: 12
- normal proposal assets: 51
- retrieval hard negatives: 12
- total retrieval assets: 63
- RFPs: 3
- retrieval queries: 48
- QA injected cases: 20

Manifest:
`evals/frozen/v1/manifest.json`

## Evaluation Order

1. synthetic proposal/RFP 작성
2. gold assertions 작성
3. benchmark freeze
4. baseline prompt 실행
5. engineered prompt variants 실행
6. 동일 evaluator로 비교
7. raw output과 metric을 `runs/`에 보존

동일 benchmark version의 gold answer는 결과를 본 뒤 수정하지 않는다. 오류 수정은 새 dataset version으로 처리한다.

## Dataset Split

### Dev
- RFP-TEST-001
- RFP-TEST-002
- retrieval 32 cases
- QA 14 cases

Prompt 개선 과정에서 사용할 수 있다.

### Holdout
- RFP-TEST-003
- retrieval 16 cases
- QA 6 cases

최종 비교 전까지 prompt 수정 근거로 직접 사용하지 않는다.

## Retrieval Hard Negatives

단순 lexical overlap으로 100%가 나오는 쉬운 benchmark를 피하기 위해 12개의 distractor asset을 추가했다.

distractor는 정답 자산과 키워드를 공유하지만 업무 목적이나 의미가 다르다.

예:
- 정책 문서 수치 검수 vs 영상 게시 전 정책정보 검수
- 온라인 개인정보 수집동의 vs 인터뷰 촬영 사용동의
- 온라인 예약 대기열 vs 오프라인 행사 혼잡 분산

## Prompt Tracks

### RFP Analyzer
Metrics:
- Mandatory Requirement Recall
- Deliverable Recall
- Numeric Fidelity
- Unsupported Addition Count
- Schema Validity

### Proposal Strategist
Metrics:
- Requirement Coverage
- Evidence Citation Coverage
- Evidence Validity
- Unsupported Company Claims
- Unsupported Quantitative Claims

### Proposal QA
Metrics:
- Critical Error Detection Recall
- False Positive Rate
- Unsupported Claim Detection
- Missing Requirement Detection
- Invalid Reference Detection

## Reproducibility

각 run은 최소 다음을 저장한다.

- run_id
- prompt_track
- prompt_version
- model
- model parameters
- dataset_version
- split
- input_case_id
- raw output
- evaluator result
- git commit

동일 track의 v0~v3 비교에서는 model과 model parameters를 동일하게 유지한다.

## Reporting Rule

포트폴리오에는 실제 실행 결과만 기재한다.

금지:
- 임의로 만든 개선율
- 실제 고객 생산성 수치처럼 보이는 synthetic 결과
- Dify 실측이 아닌 값을 Dify 성능으로 표현
- 실패 케이스 삭제
- holdout 결과를 보고 같은 benchmark version의 prompt를 재튜닝한 뒤 같은 결과를 최종치로 표현

허용:
- frozen synthetic benchmark의 측정 결과
- 명시된 실험 조건의 before/after
- raw output과 evaluator가 공개된 재현 가능한 수치
- 실패 사례와 한계를 함께 공개한 결과

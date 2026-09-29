# Evaluation Methodology v1

## Purpose

이 문서는 ProposalOps AI의 프롬프트 엔지니어링 효과를 재현 가능하게 검증하기 위한 실험 규칙을 정의한다.

이 저장소의 데이터는 synthetic/demo 데이터이며 실제 고객 프로젝트 성과가 아니다. 프롬프트 버전은 과거 운영 이력을 꾸민 것이 아니라 **비교 실험을 위해 사전에 정의한 variants**다.

## Evaluation Order

1. synthetic proposal/RFP 데이터 작성
2. 정답 기준(gold assertions) 작성
3. evaluation set freeze
4. baseline prompt 실행
5. engineered prompt variants 실행
6. 동일 evaluator로 비교
7. raw output과 metric을 runs/에 보존

평가 결과를 본 뒤 gold answer를 수정하는 행위는 금지한다. 불가피한 오류 수정은 dataset version을 올리고 변경 이유를 기록한다.

## Prompt Tracks

### RFP Analyzer
목표: RFP에서 요구사항·산출물·수치·평가기준을 빠짐없이 정확히 구조화한다.

Metrics:
- Mandatory Requirement Recall
- Deliverable Recall
- Numeric Fidelity
- Unsupported Addition Count
- Schema Validity

### Proposal Strategist
목표: 검색된 과거 자산을 근거로 사용하면서 신규 제안과 과거 사실을 혼동하지 않는다.

Metrics:
- Requirement Coverage
- Evidence Citation Coverage
- Evidence Validity
- Unsupported Company Claims
- Unsupported Quantitative Claims

### Proposal QA
목표: 제안서 초안에 삽입된 치명적 오류와 근거 누락을 탐지한다.

Metrics:
- Critical Error Detection Recall
- False Positive Rate
- Unsupported Claim Detection
- Missing Requirement Detection
- Invalid Reference Detection

## Dataset Split

- dev: prompt 개선 과정에서 열람 가능
- holdout: 최종 비교 전까지 prompt 수정에 직접 사용하지 않음

현재 초기 corpus는 pilot 단계다. 최종 포트폴리오 수치에는 별도의 holdout RFP와 proposal assets를 추가한 뒤 사용한다.

## Reproducibility

각 run은 최소 다음 정보를 저장한다.

- run_id
- prompt_track
- prompt_version
- model
- model parameters
- dataset_version
- input_case_id
- raw output
- evaluator result
- git commit

## Reporting Rule

포트폴리오에는 실제 실행 결과만 기재한다.

금지:
- 임의로 만든 개선율
- 실제 고객 생산성 수치처럼 보이는 synthetic 결과
- Dify 실측이 아닌 값을 Dify 성능으로 표현
- 실패 케이스 삭제

허용:
- 고정된 synthetic benchmark의 측정 결과
- 명시된 실험 조건에서의 before/after
- raw output과 evaluator가 공개된 재현 가능한 수치

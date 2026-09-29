# Prompt Engineering Case Study

## Portfolio Question

이 프로젝트의 핵심 질문은 "AI가 제안서를 만들 수 있는가?"가 아니다.

**같은 RFP와 같은 과거 제안서 자산을 사용할 때, 구조화된 프롬프트 엔지니어링이 결과 품질을 실제로 개선하는가?**

이를 세 개의 prompt track으로 검증한다.

## Track A — RFP Analyzer

Baseline failure hypotheses:
- 필수 요구사항 일부 누락
- 산출물 수량 혼동
- 문서에 없는 값 추정
- 출력 형식 불안정

Engineering interventions:
1. structured output
2. requirement IDs
3. source-grounded extraction
4. fail-closed unknown policy

## Track B — Proposal Strategist

Baseline failure hypotheses:
- 과거 자료와 신규 아이디어 혼합
- 관련 없는 과거 자산 사용
- 근거 없는 회사 실적 또는 수치 생성
- RFP 요구사항과 전략의 연결 누락

Engineering interventions:
1. explicit reference input
2. evidence binding
3. RFP_FACT / REFERENCE_FACT / REFERENCE_PATTERN / AI_RECOMMENDATION 분리
4. unsupported company claim blocking

## Track C — Proposal QA

Baseline failure hypotheses:
- 허위 수치 미탐지
- 요구사항 누락 미탐지
- 잘못된 reference 미탐지
- 정상 문장까지 과도하게 오류 판정

Engineering interventions:
1. explicit error taxonomy
2. severity classification
3. evidence-aware validation
4. fail-closed critical rule

## Evidence Shown in Portfolio

각 track에서 다음을 함께 공개한다.

- 동일한 input
- baseline prompt
- engineered prompt
- raw outputs
- gold answer
- evaluator
- metric comparison
- 실패 사례
- git history

결과 숫자 자체보다 **어떻게 측정했고 다시 실행할 수 있는지**를 증거로 삼는다.

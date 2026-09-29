# Frozen Evaluation Sets

이 디렉터리는 prompt 비교 실험에 사용하는 고정 평가셋을 보관한다.

## Rule

1. gold case는 prompt 결과를 보기 전에 작성한다.
2. freeze된 파일은 같은 dataset version에서 수정하지 않는다.
3. 오류 수정이 필요하면 새 version을 만든다.
4. dev set은 prompt 개선에 사용할 수 있다.
5. holdout set은 최종 비교 전까지 tuning 근거로 사용하지 않는다.

## Current Status

현재 기존 RFP-TEST-001 기반 케이스는 pilot/dev 성격이다.

최종 portfolio benchmark 전에:
- 추가 synthetic RFP
- 추가 Proposal Assets
- 별도 holdout cases
- QA injected-error cases

를 추가하고 v1 benchmark를 freeze한다.

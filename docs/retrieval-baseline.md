# Retrieval Baseline v1

## Purpose

검색 benchmark가 정답 표현을 그대로 복사해 너무 쉽게 100%가 되는 문제를 방지하기 위해 의미가 비슷하지만 목적이 다른 **hard-negative assets 12개**를 추가했다.

## Frozen corpus

- synthetic proposals: 12
- normal proposal assets: 51
- hard negatives: 12
- total retrieval assets: 63
- dev queries: 32
- holdout queries: 16

## Local lexical baseline

GitHub Actions run: `36506671960`

| Split | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---:|---:|---:|---:|
| dev | 90.62% | 100% | 100% | 0.9531 |
| holdout | 93.75% | 100% | 100% | 0.9688 |

이 결과는 Dify나 embedding 성능이 아니라 **문자 n-gram TF-IDF lexical baseline**이다.

## Useful failures

### RET-D06
질문: 게시 전 정책 수치·기간·자격조건 검수

- lexical top1: `PA-DIST-P011` 정책 문서 사실 확인
- expected: `PA-VIDEO-004-P022` 영상 게시 전 정책정보 재검수

키워드는 매우 비슷하지만 사용 맥락이 다르다.

### RET-D25
질문: 성인 디지털 교육에서 작은 행동을 직접 수행하게 하는 학습 방식

- lexical top1: `PA-EDU-003-P017`
- expected: `PA-EDU-006-P011`

둘 다 참여/행동 구조를 포함하지만 하나는 캠페인형 참여 퍼널, 다른 하나는 교육용 마이크로러닝이다.

### RET-D30
질문: 촬영 전에 얼굴·영상의 사용 채널과 기간 확인

- lexical top1: `PA-DIST-P011`
- expected: `PA-VIDEO-012-P017`

단순 문자열 유사도만으로는 동의/사용범위의 의미를 안정적으로 구분하지 못한다.

### RET-H15
질문: 정책 체험행사의 안내→체험→결과→후속정보 흐름

- lexical top1: `PA-EVENT-004-P012`
- expected: `PA-EVENT-004-P013`

같은 제안서 안에서도 사업 목적 페이지와 실제 동선 설계 페이지를 구별해야 한다.

## Interpretation

이 baseline은 일부 top1 실패가 있지만 모든 정답을 Top3 안에서는 찾았다.

따라서 이후 Dify/embedding/reranker 실험에서 볼 핵심은 **Hit@5를 억지로 높이는 것보다, 의미적으로 맞는 자산을 Top1로 올리는가**이다.

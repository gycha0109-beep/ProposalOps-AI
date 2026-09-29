# RFP Analyzer Raw Runs

이 디렉터리는 Prompt Engineering 비교 실험의 모델 원본 출력을 저장합니다.

## Expected layout

```text
benchmark-v1/
├─ dev/
│  ├─ v0_baseline/
│  ├─ v1_structured/
│  ├─ v2_grounded/
│  └─ v3_final/
└─ holdout/
   ├─ v0_baseline/
   ├─ v1_structured/
   ├─ v2_grounded/
   └─ v3_final/
```

각 run에는 모델/파라미터, prompt hash, git commit, raw output, parsed output, evaluator 결과를 함께 기록합니다.

## Holdout rule

holdout은 runner에서 기본적으로 잠겨 있습니다. 최종 prompt candidate를 freeze한 뒤에만 `--confirm-holdout`으로 실행합니다.

실패 run도 삭제하지 않습니다.

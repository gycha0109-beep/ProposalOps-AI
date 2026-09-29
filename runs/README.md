# Raw Runs

Prompt Engineering 결과의 재현성을 위해 모델 원본 출력을 저장한다.

권장 구조:

```text
runs/
├─ rfp_analyzer/
│  ├─ v0_baseline/
│  ├─ v1_structured/
│  ├─ v2_grounded/
│  └─ v3_final/
├─ proposal_strategist/
└─ proposal_qa/
```

각 run record에는 최소 다음을 보존한다.

```json
{
  "run_id": "...",
  "prompt_track": "...",
  "prompt_version": "...",
  "model": "...",
  "parameters": {},
  "dataset_version": "...",
  "input_case_id": "...",
  "git_commit": "...",
  "output": {},
  "evaluation": {}
}
```

실패한 run도 삭제하지 않는다.

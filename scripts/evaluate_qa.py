#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.qa_eval import evaluate_qa_results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--cases", default="evals/qa-injected-errors/cases.json")
    ap.add_argument("--split", required=True)
    args = ap.parse_args()

    all_cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    split = json.loads(Path(args.split).read_text(encoding="utf-8"))
    payload = json.loads(Path(args.results).read_text(encoding="utf-8"))
    result = evaluate_qa_results(payload, all_cases, split)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

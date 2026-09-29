#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.rfp_eval import evaluate_rfp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--gold", required=True)
    parser.add_argument("--raw-run", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.output).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))

    if args.raw_run:
        raw_text = payload["raw_output"]
    elif isinstance(payload, dict):
        raw_text = json.dumps(payload, ensure_ascii=False)
    else:
        raw_text = str(payload)

    result = evaluate_rfp(raw_text, gold)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

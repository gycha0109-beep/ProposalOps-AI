#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.strategy_eval import evaluate_strategy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--gold", required=True)
    ap.add_argument("--evidence-pack", required=True)
    args = ap.parse_args()

    output = json.loads(Path(args.output).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    pack = json.loads(Path(args.evidence_pack).read_text(encoding="utf-8"))
    result = evaluate_strategy(output, gold, pack)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

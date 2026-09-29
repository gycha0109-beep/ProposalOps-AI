#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib.rfp_eval import evaluate_rfp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--remove-stale-failures", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    run_files = sorted(root.rglob("run-*.json"))
    if not run_files:
        raise SystemExit(f"No raw runs found under {root}")

    updated = 0
    for path in run_files:
        record = json.loads(path.read_text(encoding="utf-8"))
        gold_path = Path(record["input"]["gold_file"])
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        record["evaluation"] = evaluate_rfp(record["raw_output"], gold)
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        updated += 1

        if args.remove_stale_failures:
            failure = (
                root
                / record["split"]
                / "_failures"
                / f'{record["prompt_version"]}-{record["input"]["rfp_id"]}-01.json'
            )
            if failure.exists():
                failure.unlink()

    print(f"re_evaluated={updated}")


if __name__ == "__main__":
    main()

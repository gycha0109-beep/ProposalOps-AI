#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--require-holdout", action="store_true")
    args = parser.parse_args()

    state = json.loads(Path(args.state).read_text(encoding="utf-8"))

    if args.require_holdout:
        if state.get("status") != "frozen":
            raise SystemExit("Holdout blocked: candidate status is not frozen.")
        if state.get("holdout_allowed") is not True:
            raise SystemExit("Holdout blocked: holdout_allowed is false.")
        if not state.get("candidate_commit"):
            raise SystemExit("Holdout blocked: candidate_commit is missing.")

    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

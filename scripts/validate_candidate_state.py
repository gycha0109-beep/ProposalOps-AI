#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    args = parser.parse_args()

    state_path = Path(args.state)
    state = load_json(state_path)
    status = state.get("status")
    prompt_path = Path(state["prompt_file"])

    if not prompt_path.exists():
        raise SystemExit(f"Prompt file does not exist: {prompt_path}")

    if status == "frozen":
        if state.get("holdout_allowed") is not True:
            raise SystemExit("Frozen candidate must have holdout_allowed=true.")
        if not state.get("candidate_commit"):
            raise SystemExit("Frozen candidate must record candidate_commit.")
        if not state.get("prompt_sha256"):
            raise SystemExit("Frozen candidate must record prompt_sha256.")

        actual_sha = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        if actual_sha != state["prompt_sha256"]:
            raise SystemExit(
                f"Frozen prompt hash mismatch: expected={state['prompt_sha256']} actual={actual_sha}"
            )

        acceptance_path = state.get("acceptance_report")
        if not acceptance_path or not Path(acceptance_path).exists():
            raise SystemExit("Frozen candidate acceptance report is missing.")

        acceptance = load_json(acceptance_path)
        if acceptance.get("accepted") is not True:
            raise SystemExit("Frozen candidate acceptance report is not accepted=true.")

    elif status == "not_frozen":
        if state.get("holdout_allowed") is not False:
            raise SystemExit("Unfrozen candidate must have holdout_allowed=false.")
        if state.get("candidate_commit") is not None:
            raise SystemExit("Unfrozen candidate must not record candidate_commit.")
    else:
        raise SystemExit(f"Unsupported candidate status: {status}")

    print(json.dumps({
        "state_file": str(state_path),
        "track": state.get("track"),
        "candidate": state.get("candidate"),
        "status": status,
        "holdout_allowed": state.get("holdout_allowed"),
        "valid": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def git_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", required=True)
    parser.add_argument("--benchmark-version", required=True)
    parser.add_argument("--acceptance", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()

    acceptance = json.loads(Path(args.acceptance).read_text(encoding="utf-8"))
    if acceptance.get("accepted") is not True:
        raise SystemExit("Candidate cannot be frozen: acceptance is not true.")
    if acceptance.get("version") not in (None, args.candidate):
        raise SystemExit("Acceptance report version does not match candidate.")

    prompt_path = Path(args.prompt)
    prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    state = {
        "track": args.track,
        "benchmark_version": args.benchmark_version,
        "candidate": args.candidate,
        "prompt_file": str(prompt_path),
        "prompt_sha256": prompt_sha256,
        "status": "frozen",
        "acceptance_report": args.acceptance,
        "acceptance_required": True,
        "holdout_allowed": True,
        "candidate_commit": git_commit(),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "note": "Frozen only after dev acceptance passed. Do not modify prompt before holdout.",
    }
    Path(args.state).write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

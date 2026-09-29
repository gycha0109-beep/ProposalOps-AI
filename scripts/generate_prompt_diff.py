#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path


DEFAULT_CONFIG = "configs/rfp-analyzer-benchmark-v1.json"


def extract_prompt_body(content: str) -> str:
    for marker in ("## Prompt", "## Role"):
        if marker in content:
            return content.split(marker, 1)[1].strip()
    raise ValueError("Prompt file must contain ## Prompt or ## Role")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--from-version", default="v0_baseline")
    parser.add_argument("--to-version", default="v3_final")
    parser.add_argument("--out")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))

    bodies = {}
    for version, prompt_path in config["versions"].items():
        path = Path(prompt_path)
        if not path.exists():
            raise SystemExit(f"Missing prompt: {path}")
        try:
            bodies[version] = extract_prompt_body(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise SystemExit(f"{path}: {exc}") from exc

    if args.check:
        if len(set(bodies.values())) != len(bodies):
            raise SystemExit("Two prompt variants have identical executable bodies.")
        print(f"validated_prompt_variants={len(bodies)}")
        return

    if args.from_version not in bodies or args.to_version not in bodies:
        raise SystemExit("Unknown prompt version.")

    diff = "\n".join(
        difflib.unified_diff(
            bodies[args.from_version].splitlines(),
            bodies[args.to_version].splitlines(),
            fromfile=args.from_version,
            tofile=args.to_version,
            lineterm="",
        )
    ) + "\n"

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(diff, encoding="utf-8")
    else:
        print(diff, end="")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def get_path(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def textify(value):
    return json.dumps(value, ensure_ascii=False).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--gold", default="evals/frozen/dev/rfp-analysis.json")
    args = ap.parse_args()

    output = json.loads(Path(args.output).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))

    passed = 0
    details = []
    for case in gold["cases"]:
        metric = case["metric"]
        ok = False

        if metric == "exact_or_semantic":
            value = get_path(output, case["path"])
            ok = case["expected"].lower() in textify(value)
        elif metric == "contains":
            value = get_path(output, case["path"])
            blob = textify(value)
            ok = all(term.lower() in blob for term in case["expected_terms"])
        elif metric == "deliverable":
            blob = textify(output.get("deliverables", []))
            expected = case["expected"]
            ok = expected["name_contains"].lower() in blob and expected["quantity"].lower() in blob
        elif metric == "evaluation_sum":
            scores = [x.get("score") for x in output.get("evaluation", [])]
            scores = [x for x in scores if isinstance(x, (int, float))]
            ok = sum(scores) == case["expected"]
        elif metric == "unknown":
            ok = get_path(output, case["path"]) == case["expected"]
        elif metric == "requirement_terms":
            blob = textify(output.get("requirements", []))
            ok = all(term.lower() in blob for term in case["expected_terms"])
        elif metric == "requirement_present":
            blob = textify(output.get("requirements", []))
            ok = case["expected_term"].lower() in blob
        elif metric == "unsupported_addition":
            blob = textify(output)
            ok = not any(term.lower() in blob for term in case["forbidden_terms"])

        passed += int(ok)
        details.append({"id": case["id"], "pass": ok})

    total = len(gold["cases"])
    print(json.dumps({
        "track": "rfp_analyzer",
        "passed": passed,
        "total": total,
        "score": round(passed / total, 4) if total else 0,
        "details": details
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

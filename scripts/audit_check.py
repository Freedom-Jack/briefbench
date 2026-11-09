"""Check the checker before a test: label reports yourself, without seeing the check's verdict, and compare
(docs/experiment-protocol.md, section 4, step 2). Standard library and briefbench only.

    uv run python scripts/audit_check.py --experiment NAME --answers ANSWERS.json [--count 20] [--file report.md]

NAME is usually the calibration experiment. ANSWERS.json gives each task's planted answer: the list a generator's
`explain` prints, whose items have an "id" and a "driver", or a JSON object mapping each task id to its answer. The
script picks --count arms' reports at random from the experiment's noise checks and trials, reading each from the
diff the bench kept, and shows it with its task's planted answer, never with its arm or its check's verdict. For
each, you say whether the report names the planted answer as its main driver. Your labels go to
audits/<NAME>.json in the data folder; then the script prints how often the check agreed with you, and where not.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

from briefbench import experiment
from briefbench.log import data_dir, read_entries, utc_now


def report_in(diff: Path, name: str) -> str | None:
    """The file `name` as the arm's diff holds it, new: its added lines. None when the arm didn't write it."""
    try:
        lines = diff.read_text(errors="replace").splitlines()
    except OSError:
        return None
    found, inside = [], False
    for line in lines:
        if line.startswith("diff --git "):
            inside = line.endswith(f" b/{name}")
        elif inside and line.startswith("+") and not line.startswith("+++"):
            found.append(line[1:])
    return "\n".join(found) or None


def reports(exp: dict, name: str) -> list[dict]:
    """Each arm's report in the experiment's noise checks and trials, with its task and the check's verdict."""
    path, created = data_dir(os.environ) / "log.jsonl", exp.get("created")
    found = []
    for e in read_entries(path) if path.exists() else []:
        if (e.get("experiment") != exp["name"] or e.get("experiment_created", created) != created
                or e.get("kind") not in ("aa", "trial")):
            continue
        task = ((e.get("task") or {}).get("source") or {}).get("id")
        for side in "ab":
            check, text = e["arms"][side].get("check"), report_in(Path(e["output"]) / f"{side}.diff", name)
            if task and check and text:
                found.append({"trial": e["id"], "side": side, "task": task, "passed": check["passed"], "text": text,
                              "diff": str(Path(e["output"]) / f"{side}.diff")})
    return found


def answers(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text())
    return {item["id"]: item["driver"] for item in data} if isinstance(data, list) else dict(data)


def main(argv=None, stdin=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--experiment", required=True, help="the experiment whose reports you label")
    parser.add_argument("--answers", type=Path, required=True, help="each task's planted answer, as JSON")
    parser.add_argument("--count", type=int, default=20, help="how many reports to label (default 20)")
    parser.add_argument("--file", default="report.md", help="the file each arm writes (default report.md)")
    parser.add_argument("--seed", type=int, help="the seed for the random choice (default: a fresh one)")
    args = parser.parse_args(argv)
    stdin = stdin or sys.stdin
    exp, keys = experiment.load(args.experiment, os.environ), answers(args.answers)
    pool = [r for r in reports(exp, args.file) if r["task"] in keys]
    if not pool:
        print(f"No report with a known answer in experiment {exp['name']}.", file=sys.stderr)
        return 2
    chosen = random.Random(args.seed).sample(pool, min(args.count, len(pool)))
    labels = []
    for n, r in enumerate(chosen, 1):
        print(f"\nReport {n} of {len(chosen)}. The planted answer: {keys[r['task']]}\n")
        print("  " + r["text"].rstrip().replace("\n", "\n  ") + "\n")
        said = ""
        while said not in ("y", "n"):
            print("Does it name the planted answer as its main driver? (y/n): ", end="", flush=True)
            line = stdin.readline()
            if not line:
                print("\nInput ended: nothing was saved.", file=sys.stderr)
                return 130
            said = line.strip().lower()
        labels.append({k: r[k] for k in ("trial", "side", "task", "passed")} | {"names_answer": said == "y"})
    path = data_dir(os.environ) / "audits" / f"{exp['name']}.json"
    experiment.write_private(path, {"experiment": exp["name"], "created": utc_now(), "file": args.file,
                                    "labels": labels})
    wrong = [(label, r) for label, r in zip(labels, chosen) if label["names_answer"] != label["passed"]]
    print(f"\nThe check agreed with your labels on {len(labels) - len(wrong)} of {len(labels)} reports. Labels saved in "
          f"{path}.")
    for label, r in wrong:
        print(f"  You said the report {'names' if label['names_answer'] else 'does not name'} the planted answer; the "
              f"check {'passed' if label['passed'] else 'failed'} it: {r['diff']}")
    if wrong:
        print("Read each one. If the check was wrong, fix the checker, make a new version of the materials and "
              "calibrate again, before any test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Review the fidelity of the briefs written in an experiment's unattended trials, apart from their outcomes (docs/build-
plan.md, P3, step 3). Standard library and briefbench only.

    uv run python scripts/review_briefs.py --experiment NAME

In a trial run from a task file, nobody is there to review the brief the skill wrote, so each one waits. This script
shows the briefs that the experiment's fidelity policy, frozen at `init`, asks you to review: all of arm B's, or a
random sample drawn from the experiment once all the rule's trials are in, so that nobody chooses which. You see each
one with only what the request said: the prompt, and the skill's questions with the stand-in requester's answers. You
never see a check, an outcome, a diff or the other arm. For each, you answer the three fidelity questions, as the
requester would. Each review goes to the log as a `fidelity` line at once, so you can stop and go on later. Review every
brief before you read `briefbench score`, which counts the reviews and applies the policy.

Single-arm bench runs support review of every B brief, independently of the screen's check outcomes. Those reviews
do not turn the runs into paired confirmatory trials. A paired-trial sampling policy is refused for single-arm runs.
"""
from __future__ import annotations

import argparse
import os
import sys

from briefbench import experiment, score
from briefbench.cli import FIDELITY
from briefbench.log import append, data_dir, header, read_entries
from briefbench.presets import secret_values


def shown(trial: dict, spec: str) -> str:
    """A brief as you review it: the request, the skill's questions with their answers, and the brief."""
    task = trial["task"]
    asked = [q for q in task.get("questions") or [] if q["skill"] == spec]
    lines = ["What the request said:", "  " + task["prompt"].replace("\n", "\n  "), ""]
    if asked:
        who = "the stand-in requester, from the task's facts" if task.get("answered_by") == "stand-in" else "you"
        lines += [f"The skill's questions, answered by {who}:"]
        lines += [f"  Q: {q['q']}\n  A: {q['a'] or '(not answered)'}" for q in asked] + [""]
    lines += ["The brief arm B got:", "  " + trial["prompts"]["b"].rstrip().replace("\n", "\n  "), ""]
    return "\n".join(lines)


def main(argv=None, stdin=None, stdout=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--experiment", required=True, help="the experiment whose briefs you review")
    args = parser.parse_args(argv)
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    exp = experiment.load(args.experiment, os.environ)
    path = data_dir(os.environ) / "log.jsonl"
    queue, why = score.review_queue(exp, read_entries(path) if path.exists() else [])
    if why:
        print(why, file=sys.stderr)
        return 2
    if not queue:
        print("Every brief chosen for review has its review.", file=stdout)
        return 0
    print(f"{len(queue)} brief{'s' if len(queue) != 1 else ''} to review. Judge each against what the request said, "
          "as the requester would. Nothing here says how any trial came out.", file=stdout)
    for n, trial in enumerate(queue, 1):
        print(f"\nBrief {n} of {len(queue)}.\n\n{shown(trial, exp['b']['spec'])}", file=stdout)
        review = {}
        for key, question in FIDELITY:
            said = ""
            while said not in ("y", "n"):
                print(f"{question} (y/n): ", end="", file=stdout, flush=True)
                line = stdin.readline()
                if not line:
                    print(f"\nInput ended: the {n - 1} reviews before this one are kept.", file=sys.stderr)
                    return 130
                said = line.strip().lower()
            review[key] = said == "y"
        append(path, header("fidelity") | {"experiment": exp["name"], "experiment_created": exp.get("created"),
                                           "trial": trial["id"], "side": "b", **review}, secret_values(os.environ))
    print(f"\nDone: {len(queue)} review{'s' if len(queue) != 1 else ''} saved in the log. `briefbench score "
          f"{exp['name']}` counts them.", file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Run task files through `briefbench ab --task`, one trial after another, unattended.

    uv run python scripts/run_tasks.py --experiment NAME [--limit N] [--aa] TASKS.txt

TASKS.txt lists task files, one per line, relative to its own folder, in the order the experiment runs them. The
experiment must be scored by the check alone (`init --scoring check`). The runner skips a task that already has a
line of the same kind in this experiment's log: a trial, or with --aa a noise check. So a stopped run picks up where
it left off, and noise checks and trials never use up each other's tasks.

It stops, so that you can look before more plan usage is spent:
- after --limit trials;
- when a trial step fails, including an arm stopped by a usage limit or an outage. `ab` logs the trial as failed,
  and the next run retries that task once, as the protocol asks; a task that failed twice is a missing outcome;
- when an arm's output names the data folder, where the answer keys and records live;
- at any other error, or when you cancel.
After each trial it runs `briefbench clean`. Standard library and briefbench only.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

from briefbench import cli, experiment
from briefbench.log import data_dir, read_entries
from briefbench.tasks import load


def lines(exp: dict) -> list[dict]:
    """This experiment's log lines; lines of an older experiment with the same name don't count, as in score."""
    path = data_dir(os.environ) / "log.jsonl"
    created = exp.get("created")
    return [e for e in (read_entries(path) if path.exists() else [])
            if e.get("experiment") == exp["name"] and e.get("experiment_created", created) == created]


def seen(entries: list[dict], sha256: str, aa: bool) -> dict[str, int]:
    """How many compared lines of this run's kind, and how many failed ones, the log holds for one task file."""
    counts = {"done": 0, "failed": 0}
    for e in entries:
        if ((e.get("task") or {}).get("source") or {}).get("sha256") != sha256:
            continue
        if e.get("kind") == ("aa" if aa else "trial"):
            counts["done"] += 1
        elif e.get("kind") == "failed" and bool(e.get("aa")) == aa:
            counts["failed"] += 1
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("tasks", type=Path, help="a file listing task files, one per line")
    parser.add_argument("--experiment", required=True, help="the experiment, frozen with briefbench init")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many trials (default: no limit)")
    parser.add_argument("--aa", action="store_true", help="noise checks: treatment A in both arms")
    args = parser.parse_args(argv)
    exp = experiment.load(args.experiment, os.environ)
    if exp.get("scoring", "pick") != "check":
        print(f"Experiment {exp['name']} isn't scored by the check alone, so it needs your picks; freeze one with "
              "--scoring check.", file=sys.stderr)
        return 2
    files = [args.tasks.parent / line.strip() for line in args.tasks.read_text().splitlines() if line.strip()]
    tasks = [load(f) for f in files]           # checks every file before the first trial runs
    ran = 0
    for task in tasks:
        counts = seen(lines(exp), task["sha256"], args.aa)
        if counts["done"] or counts["failed"] >= 2:      # done, or failed twice: a missing outcome
            continue
        print(f"Task {task['id']} ({ran + 1}{f' of {args.limit}' if args.limit else ''})...", flush=True)
        argv = ["ab", "--task", task["file"], "--experiment", exp["name"]] + (["--aa"] if args.aa else [])
        code = cli.run(argv, stdin=io.StringIO(""))
        cli.run(["clean"], stdin=io.StringIO(""), stderr=io.StringIO())
        if code == 4:
            print(f"Stopped: a step of task {task['id']}'s trial failed, and it is logged as failed. Its log says "
                  "why; the next run retries the task once.", file=sys.stderr)
            return 4
        if code != 0:
            print(f"Stopped at task {task['id']}: briefbench exited with {code}.", file=sys.stderr)
            return code
        ran += 1
        newest = lines(exp)[-1]
        if any(newest["arms"][side].get("looked_outside") for side in "ab"):
            print(f"Stopped: an arm's output in task {task['id']}'s trial names the data folder. Read its log in "
                  f"{newest['output']} before going on.", file=sys.stderr)
            return 1
        if args.limit and ran >= args.limit:
            break
    print(f"Ran {ran} trial{'s' if ran != 1 else ''}. `briefbench score {exp['name']}` reports on them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

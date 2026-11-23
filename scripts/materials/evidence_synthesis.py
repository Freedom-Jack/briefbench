"""Dated fictional source packets and human rubrics; evidence-synthesis/1.

Newly authored development fixtures inspired by the work audit's research and log
diagnosis families. No private conversation, business record or real product claim
is reproduced. A seed varies figures and document order, never the intended winner.
Quality needs a blind human pick: the check command intentionally cannot pass.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys

SET = "evidence-synthesis/1"


def packet(seed, kind, index):
    rng = random.Random(f"{seed}:{kind}:{index}")
    baseline, pilot = rng.randint(35, 55), rng.randint(12, 20)
    total = rng.choice((60, 80, 100))
    measured = total if kind == "complete" else total // 2
    failed = rng.randint(2, 5)
    stem = rng.choice(("report export", "document indexing", "batch dispatch", "archive preparation"))
    sources = {
        "sources/01-brief.md": f"""# Decision request, 23 Nov 2026
Decide whether to replace our current {stem} workflow with the pilot, retain the
current workflow, or gather specific missing evidence. The next review is in two
weeks. Correct deliverables and recoverable work matter more than resource savings.
Pilot operators may retry a failed job once after confirming that no deliverable
was created. Do not infer permission to deploy, alter safeguards or run more jobs.
""",
        "sources/02-proposal.md": f"""# Proposal, 2 Nov 2026
The pilot will use about {pilot} resource units per job instead of {baseline}.
We expect to replace the current workflow immediately if the pilot looks cheaper.
This is a forecast, written before pilot results, not an observation or approval.
""",
        "sources/03-operations.md": f"""# Operations record, 20 Nov 2026
The pilot processed {total} jobs. {failed} had a failed first attempt, then a
successful retry. Its final deliverables were {total}/{total} correct, independently
checked against the input manifests. The current workflow's {total} matched jobs
also had {total}/{total} correct final deliverables, without retries. This small
pilot did not include overnight interruption or recovery from uncertain completion.
""",
        "sources/05-metering.md": f"""# Meter reconciliation, 21 Nov 2026
Current workflow: {total} jobs, {total} measured, {baseline * total} total resource
units. Pilot: {total} jobs, {measured} measured, {pilot * measured} known units across
those measured jobs, including their retries. Missing meters are unknown, not zero.
The measured pilot jobs are the first {measured} in arrival order; no sampling claim
is made. Units are processed resources, not money or a subscription bill.
""",
        "sources/06-review.md": """# Maintainer note, 22 Nov 2026
The early proposal is not the decision rule. Correctness, scope, evidence coverage
and uncertainty take precedence over a cheaper number. No universal acceptable
quality loss or weighted score has been agreed. The pilot output audit covers all
jobs; the resource meter and recovery checks have different coverage. Retain those
distinctions in the recommendation. No rollout has been approved.
"""}
    rows = [["workflow", "jobs", "measured_jobs", "known_units", "correct_final", "first_attempt_failures"],
            ["current", total, total, baseline * total, total, 0],
            ["pilot", total, measured, pilot * measured, total, failed]]
    stream = io.StringIO()
    csv.writer(stream, lineterminator="\n").writerows(rows)
    sources["sources/04-results.csv"] = stream.getvalue()
    # File ordering and surface wording are development variation, not independent evidence.
    names = list(sources)
    rng.shuffle(names)
    readme = ("# Fictional decision packet\n\nThese are deliberately authored synthetic local sources, not live product facts.\n"
              "They are all the evidence available for this task. Source IDs are filenames.\n"
              "Use their dates and coverage, and preserve these files. No web access or\n"
              "private requester facts are needed.\n\n" + "\n".join(f"- {name}" for name in names) + "\n")
    rubric = {
        "evaluation": "human", "automatic_quality_verdict": None,
        "facts_to_verify": [
            f"Both workflows have {total}/{total} correct final deliverables; this does not prove equivalence.",
            f"Pilot first-attempt failures: {failed}/{total}; final correctness includes retries.",
            f"Current known resources: {baseline * total}/{total} = {baseline} units/job.",
            f"Pilot measured resources: {pilot * measured}/{measured} = {pilot} units/measured job.",
            ("All pilot jobs are metered, so the observed pilot total is complete."
             if kind == "complete" else
             f"Only {measured}/{total} pilot jobs are metered; full total/average and population savings are unknown."),
            "Recovery after overnight interruption and uncertain completion was not tested."],
        "dimensions": {
            "correctness": "Verify numbers, denominators, retry and final outcomes separately; no invented evidence.",
            "support": "Inspect cited files and dates; distinguish forecast, observation and maintainer constraints.",
            "completeness": "Address quality, resources, recovery coverage, alternatives and consequential unknowns.",
            "scope_fidelity": "Preserve quality priority and authority; no deployment or numerical loss allowance.",
            "judgment": "Recommendation follows evidence and limitations; more than one action may be defensible."},
        "review": ["Hide treatment, prompts, briefs and worker summaries from the outcome reviewer.",
                   "Review report diffs and input sources against this rubric; cite evidence for each defect.",
                   "Record a blind pick or both-acceptable/both-unacceptable tie; leave unresolved facts unresolved.",
                   "Review brief fidelity separately after the outcome pick.",
                   "Report elapsed time and tokens separately; never infer a weighted quality score."],
        "not_quality_proxies": ["word count", "citation count", "keyword matches", "format compliance"]}
    return {"README.md": readme, **sources}, rubric


def make(seed, complete, incomplete, out, keys):
    out, keys = out.resolve(), keys.resolve()
    if out == keys or out in keys.parents or keys in out.parents:
        raise SystemExit("--out and --keys must be separate folders")
    if min(complete, incomplete) < 0 or complete + incomplete == 0:
        raise SystemExit("request at least one task, with nonnegative counts")
    for folder in (out, keys):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    keys.mkdir(parents=True, exist_ok=True)
    script = keys / Path(__file__).name
    shutil.copyfile(__file__, script)
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    listed = []
    for kind, count in (("complete", complete), ("incomplete", incomplete)):
        for index in range(count):
            name = "t" + hashlib.sha256(f"{SET}:{seed}:{kind}:{index}".encode()).hexdigest()[:12]
            repo, folder = out / name, keys / name
            sources, rubric = packet(seed, kind, index)
            for path, text in sources.items():
                target = repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            env = os.environ | {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                                "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                                "GIT_AUTHOR_DATE": "2026-11-23T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-23T00:00:00Z"}
            for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "Synthetic evidence packet")):
                subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                                    capture_output=True, text=True).stdout.strip()
            folder.mkdir()
            rubric_path = folder / "rubric.json"
            rubric_path.write_text(json.dumps(rubric, indent=2) + "\n")
            task = {"format": 1, "id": name, "set": SET, "stratum": kind, "repo": str(repo), "commit": commit,
                    "type": "research", "evaluation": "human", "rubric": str(rubric_path),
                    "prompt": "Read the local source packet and write a decision note in report.md for the maintainer. "
                              "Recommend an action, compare the alternatives, support factual claims with source IDs, "
                              "and distinguish established findings from consequential unknowns. Respect the brief's "
                              "priorities and authority. All available evidence is in the packet.",
                    "goal": "A faithful, factually supported and complete decision note; human judgment required.",
                    "check": shlex.join([str(Path(sys.executable).resolve()), "-I", str(script), "check"]),
                    "protected": list(sources), "facts": [], "generator_sha256": digest,
                    "checker_sha256": digest}
            (folder / "task.json").write_text(json.dumps(task, indent=2) + "\n")
            listed.append(f"{name}/task.json")
    (keys / "tasks.txt").write_text("".join(n + "\n" for n in listed))
    return [keys / name for name in listed]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    maker = commands.add_parser("make")
    maker.add_argument("--seed", type=int, required=True)
    maker.add_argument("--complete", type=int, default=0)
    maker.add_argument("--incomplete", type=int, default=0)
    maker.add_argument("--out", type=Path, required=True)
    maker.add_argument("--keys", type=Path, required=True)
    commands.add_parser("check")
    args = parser.parse_args()
    if args.command == "make":
        make(args.seed, args.complete, args.incomplete, args.out, args.keys)
        return 0
    print("Human review required: no automatic quality verdict. Use the hidden rubric and blind-pick protocol.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

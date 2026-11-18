"""Requests with a missing fact, for the skill's first growth round, "let the agent interview you"
(claims/ask-questions-first.md). Standard library only.

    uv run python scripts/materials/missing_fact.py make --seed S --gap G --no-gap N --out REPOS --keys KEYS
    uv run python scripts/materials/missing_fact.py explain --seed S --gap G --no-gap N      (after the experiment)
    python3 -I KEYS/missing_fact.py check --key KEY [--report report.md]                   (the bench runs this)

Each task is a small git repo with a README and one CSV, one row per customer, order or shipment, and a request for one
rate, for a meeting. In a `gap` task the prompt leaves out a fact the requester knows and the rate depends on: which
group a decision is about, or from which month a change counts. The prompt shows that something is missing ("one group
of our customers", "since the change"), as people write when they forget that the reader doesn't know. The task file's
`facts` hold that fact and two that don't matter, in a random order, for the stand-in requester. In a `no-gap` task the
prompt states the fact itself, so asking about it can only cost. The check reads the report's last `Answer:` line and
passes the rate computed with the fact, to within 0.15 points.

The data never depends on the missing fact. Every column's levels move the rate by similar amounts, and the rate rises
month by month, so no group or month is marked out; the fact is drawn only afterwards, among the groups or months whose
rate stands apart. So the repo can't give the fact away, and a guess fails: the rate with the fact is at least 3 points
from the rate over everyone and at least 1 point from the rate of every other group, month or start month someone might
pick, and the group is never the one whose rate stands out the most. Three domains take turns, and so do the two
kinds of fact.

Set `missing-fact/1`. The repos go under REPOS, everything else under KEYS: the task files, the answer keys, a copy of
this script that the checks run, and the list of tasks. Keep KEYS apart from REPOS, for example
~/.briefbench/keys/<name> beside ~/.briefbench/materials/<name>. Folders get opaque names, and the seed is written only
in KEYS, so nothing an agent sees in its repo says which task it is. The protection is where the keys are kept, and the
bench's own steps: each arm works in a clone of its own and can't read the data folder or the keys. `explain` prints each
task's fact and answer, regenerated from the seed: run it only after the experiment. Each task file names its kind
(its `stratum`), `gap` or `no-gap`, so that an experiment frozen with `init --strata gap,no-gap` tests the two apart.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SET = "missing-fact/1"
KINDS = ("gap", "no-gap")
MONTHS = ("January", "February", "March", "April", "May", "June")
TOLERANCE = 0.15                  # points of the percentage: one decimal, rounded either way
# Each domain: its table, its columns (levels, weights, what the column is, how a request names one level's group), how
# a request asks for the rate with the fact missing or stated, how the requester says the fact, and two facts that
# don't change the answer.
DOMAINS = (
    {"name": "churn", "file": "customers.csv", "id": "customer_id", "date": "signup_month", "outcome": "churned",
     "rate": "churn rate", "readme": "Customers who signed up between January and June 2026, one row each. `churned` "
                                     "is yes when the customer cancelled within 90 days of signing up.",
     "when": "The month the customer signed up (YYYY-MM)",
     "factors": {
         "plan": (("basic", "pro", "team"), (5, 3, 2), "the subscription plan", "customers on the {Level} plan"),
         "region": (("na", "eu", "apac", "latam"), (4, 3, 2, 1), "the billing region", "customers in {LEVEL}"),
         "channel": (("organic", "ads", "referral", "partner"), (4, 3, 2, 2), "how the customer signed up",
                     "customers who came in through {level}"),
         "onboarding_completed": (("yes", "no"), (7, 3), "whether the customer finished onboarding", None)},
     "group": ("We're planning a retention offer for one group of our customers, and I need that group's churn rate "
               "for the proposal.", "We're planning a retention offer for {group}, and I need their churn rate for "
               "the proposal.", "The retention offer is only for {group}."),
     "window": ("Our pricing changed this year, and I need the churn rate since the change for the board.",
                "Our pricing changed for customers who signed up from {month} 2026 on, and I need the churn rate "
                "since then for the board.", "The pricing change applied to customers who signed up from {month} 2026 "
                                             "on."),
     "fillers": ("The proposal goes to the leadership meeting on Thursday.",
                 "Keep the write-up short: a page is plenty.")},
    {"name": "returns", "file": "orders.csv", "id": "order_id", "date": "order_month", "outcome": "returned",
     "rate": "return rate", "readme": "Online orders placed between January and June 2026, one row each. `returned` "
                                      "is yes when any item in the order was sent back.",
     "when": "The month the order was placed (YYYY-MM)",
     "factors": {
         "category": (("apparel", "electronics", "home", "beauty"), (4, 2, 3, 2), "the main product category",
                      "{level} orders"),
         "warehouse": (("east", "west", "central"), (4, 4, 3), "the warehouse that shipped the order",
                       "orders shipped from the {level} warehouse"),
         "discount_code": (("yes", "no"), (3, 7), "whether a discount code was used", None),
         "first_order": (("yes", "no"), (3, 7), "whether it was the customer's first order", None)},
     "group": ("We're trying new packaging for one kind of order, and I need the return rate for those orders for "
               "the review.", "We're trying new packaging for {group}, and I need their return rate for the review.",
               "The new packaging is only for {group}."),
     "window": ("Our returns policy changed this year, and I need the return rate since the change for the review.",
                "Our returns policy changed for orders placed from {month} 2026 on, and I need the return rate since "
                "then for the review.", "The new returns policy applies to orders placed from {month} 2026 on."),
     "fillers": ("The review is with the operations team next week.", "A short summary is enough; no charts needed.")},
    {"name": "delays", "file": "shipments.csv", "id": "shipment_id", "date": "ship_month", "outcome": "late",
     "rate": "late-delivery rate", "readme": "Shipments sent between January and June 2026, one row each. `late` is "
                                             "yes when the shipment arrived after its promised date.",
     "when": "The month the shipment left (YYYY-MM)",
     "factors": {
         "carrier": (("swiftpost", "northfreight", "parcelco"), (4, 3, 3), "the delivery carrier",
                     "shipments carried by {Level}"),
         "origin_hub": (("riverside", "lakeside", "hillcrest"), (4, 3, 3), "the hub the shipment left from",
                        "shipments from the {Level} hub"),
         "package_size": (("small", "medium", "large"), (4, 4, 2), "the package size", "{level} packages"),
         "weekend_dispatch": (("yes", "no"), (2, 8), "whether it was dispatched on a weekend", None)},
     "group": ("We're changing how we handle one group of our shipments, and I need that group's late-delivery rate "
               "for the planning meeting.", "We're changing how we handle {group}, and I need their late-delivery "
               "rate for the planning meeting.", "The change only covers {group}."),
     "window": ("We changed our routing this year, and I need the late-delivery rate since the change for the planning "
                "meeting.", "We changed our routing for shipments sent from {month} 2026 on, and I need the "
                "late-delivery rate since then for the planning meeting.",
                "The new routing applies to shipments sent from {month} 2026 on."),
     "fillers": ("The planning meeting is on the 20th.", "Plain numbers are fine; it doesn't need to look polished.")},
)
ASK = "Please work it out from data/{file} and write it up in report.md."
FORMAT_LINE = "End the report with a line `Answer: <rate>` giving the {rate} as a percentage with one decimal, such as "\
              "`Answer: 12.3%`."
ANSWER = re.compile(r"^\W*answer\W*?(?::|\s[-–—])\s*(.+?)\s*$", re.IGNORECASE)
NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(\s*%)?")


def domain_of(task: dict) -> dict:
    return next(d for d in DOMAINS if d["name"] == task["domain"])


def order(gap: int, complete: int) -> list[tuple[str, int]]:
    """The tasks in the order they run, (kind, k) for the k-th of its kind: the two kinds spread evenly."""
    totals, done, out = {"gap": gap, "no-gap": complete}, {"gap": 0, "no-gap": 0}, []
    for _ in range(gap + complete):
        kind = min((k for k in KINDS if done[k] < totals[k]), key=lambda k: ((done[k] + 0.5) / totals[k], k))
        out.append((kind, done[kind]))
        done[kind] += 1
    return out


def tables(task: dict) -> list[list[str]]:
    """The CSV, header first. Each level of each column with more than two levels moves the outcome's chance by up to
    8 points, a yes/no column by up to 2, and the chance rises by the same few points every month. Nothing here depends
    on the task's fact, which is chosen afterwards (`plan`)."""
    domain, rng = domain_of(task), random.Random(task["data_seed"])
    factors = domain["factors"]
    shifts = {name: [rng.uniform(-0.08, 0.08) if len(spec[0]) > 2 else rng.uniform(-0.02, 0.02) for _ in spec[0]]
              for name, spec in factors.items()}
    rows = [[domain["id"], domain["date"], *factors, domain["outcome"]]]
    for n in range(task["rows"]):
        month = rng.randint(1, 6)
        levels = {name: rng.choices(range(len(spec[0])), spec[1])[0] for name, spec in factors.items()}
        chance = task["base"] + task["slope"] * (month - 1) + sum(shifts[name][i] for name, i in levels.items())
        rows.append([f"{domain['id'][0].upper()}{n + 1:05d}", f"2026-{month:02d}",
                     *(factors[name][0][i] for name, i in levels.items()),
                     "yes" if rng.random() < min(1.0, max(0.0, chance)) else "no"])
    return rows


def rates(domain: dict, rows: list[list[str]]) -> dict:
    """The rate, in percent, over everyone, and for each group (column, level), month and start month someone
    might compute."""
    head, body = rows[0], rows[1:]
    def pct(picked):
        picked = list(picked)
        return 100 * sum(r[-1] == "yes" for r in picked) / len(picked) if picked else None
    found = {("all",): pct(body)}
    for c, column in enumerate(head[2:-1], start=2):
        for level in sorted({r[c] for r in body}):
            found[("group", column, level)] = pct(r for r in body if r[c] == level)
    for month in range(1, 7):
        found[("month", month)] = pct(r for r in body if int(r[1][-2:]) == month)
        found[("from", month)] = pct(r for r in body if int(r[1][-2:]) >= month)
        found[("before", month)] = pct(r for r in body if int(r[1][-2:]) < month)
    return {k: v for k, v in found.items() if v is not None}


def facts_for(domain: dict, rows: list[list[str]], kind_of_fact: str) -> list[tuple]:
    """The facts a task could be about, given its data: a group of a column with more than two levels, or a start
    month from March to June, whose rate is at least 3 points from the rate over everyone and at least 1 point from
    every other rate a guess would give: another group for a group; a month, another start month or the months before
    for a start month. A group is never the one whose rate stands out the most."""
    found = rates(domain, rows)
    overall = found[("all",)]
    if kind_of_fact == "group":
        top = max((k for k in found if k[0] == "group"), key=lambda k: abs(found[k] - overall))
        picks = [k for k in found if k[0] == "group" and domain["factors"][k[1]][3] and k != top]
    else:
        picks = [("from", month) for month in range(3, 7)]
    return [k for k in picks if abs(found[k] - overall) >= 3
            and all(abs(found[k] - found[other]) >= 1 for other in rivals(found, kind_of_fact) if other != k)]


def rivals(found: dict, kind_of_fact: str) -> list[tuple]:
    """The rates a guess would give instead: the other groups for a group; the months, start months and months before
    for a start month."""
    return [k for k in found if k[0] in (("group",) if kind_of_fact == "group" else ("month", "from", "before"))]


def plan(seed: int, kind: str, k: int) -> dict:
    """Everything about the k-th task of one kind, drawn from the seed: the domain and the kind of fact (they take
    turns), the data, and then the fact, among those the data leaves apart (`facts_for`); data is drawn again until
    one is."""
    rng = random.Random(f"{SET}:{seed}:{kind}:{k}")
    domain = DOMAINS[(k + seed) % len(DOMAINS)]
    kind_of_fact = ("group", "window")[(k // len(DOMAINS) + seed) % 2]
    task = {"kind": kind, "k": k, "domain": domain["name"], "fact_kind": kind_of_fact,
            "template_seed": rng.getrandbits(32), "name": f"t{rng.getrandbits(48):012x}"}
    for attempt in range(1, 101):
        task |= {"data_seed": rng.randrange(2 ** 32), "rows": rng.randrange(2000, 3601, 50),
                 "base": round(rng.uniform(0.05, 0.10), 3), "slope": round(rng.uniform(0.025, 0.04), 4),
                 "attempts": attempt}
        rows = tables(task)
        if choices := facts_for(domain, rows, kind_of_fact):
            pick = rng.choice(choices)
            return task | {"fact": list(pick), "expected": round(rates(domain, rows)[pick], 4)}
    raise RuntimeError(f"no data for task {task['name']} left a fact apart in 100 draws")


def wording(domain: dict, fact: list) -> dict:
    """How a request names the fact: the group (customers on the Team plan) or the start month (April)."""
    if fact[0] == "group":
        _levels, _weights, _doc, phrase = domain["factors"][fact[1]]
        level = fact[2]
        return {"group": phrase.format(level=level, Level=level.capitalize(), LEVEL=level.upper())}
    return {"month": MONTHS[fact[1] - 1]}


def prompt(task: dict) -> str:
    domain = domain_of(task)
    missing, stated, _said = domain["group" if task["fact_kind"] == "group" else "window"]
    request = missing if task["kind"] == "gap" else stated.format(**wording(domain, task["fact"]))
    return " ".join((request, ASK.format(file=domain["file"]), FORMAT_LINE.format(rate=domain["rate"])))


def said(task: dict) -> str:
    """The fact as the requester says it: The retention offer is only for customers on the Team plan."""
    domain = domain_of(task)
    return domain["group" if task["fact_kind"] == "group" else "window"][2].format(**wording(domain, task["fact"]))


def facts(task: dict) -> list[str]:
    """What the requester knows: the fact, and two that don't change the answer, in an order drawn for the task."""
    found = [said(task), *domain_of(task)["fillers"]]
    random.Random(task["template_seed"]).shuffle(found)
    return found


def readme(task: dict) -> str:
    domain = domain_of(task)
    lines = ["# Data export", "", domain["readme"], "", f"## data/{domain['file']}", "", "| Column | Meaning |",
             "| --- | --- |", f"| `{domain['id']}` | Row id |", f"| `{domain['date']}` | {domain['when']} |"]
    lines += [f"| `{name}` | {spec[2].capitalize()}: {', '.join(spec[0])} |" for name, spec in domain["factors"].items()]
    lines += [f"| `{domain['outcome']}` | yes or no |"]
    return "\n".join(lines) + "\n"


def git(repo: Path, *args: str) -> str:
    """git with a fixed author, dates and settings, and none of yours, so a seed always gives the same commit."""
    stamp, who = "2026-10-01T00:00:00Z", ("briefbench", "briefbench@example.invalid")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {
        "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp, "GIT_AUTHOR_NAME": who[0], "GIT_AUTHOR_EMAIL": who[1],
        "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1], "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}",
                           "-c", "init.defaultBranch=main", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def make(seed: int, gap: int, complete: int, out: Path, keys: Path) -> list[Path]:
    """Write `gap` + `complete` task repos under `out` and their task files, keys and checker under `keys`, with
    keys/tasks.txt listing the task files in order (`order`). Both folders must be new or empty."""
    out, keys = out.resolve(), keys.resolve()
    if out == keys or out in keys.parents or keys in out.parents:
        raise SystemExit("--out and --keys must be separate folders, neither inside the other.")
    if gap < 0 or complete < 0 or gap + complete == 0:
        raise SystemExit("--gap and --no-gap are how many tasks of each kind to write: at least one in all.")
    for folder in (out, keys):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} isn't empty; make writes a fresh set.")
        folder.mkdir(parents=True, exist_ok=True)
    script = keys / "missing_fact.py"         # the checks run this copy, so they outlive the checkout that made them
    shutil.copyfile(Path(__file__).resolve(), script)
    generator = hashlib.sha256(script.read_bytes()).hexdigest()
    files = []
    for kind, k in order(gap, complete):
        task = plan(seed, kind, k)
        domain = domain_of(task)
        repo = out / task["name"]
        (repo / "data").mkdir(parents=True)
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(tables(task))
        (repo / "data" / domain["file"]).write_text(buffer.getvalue())
        (repo / "README.md").write_text(readme(task))
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "Data export")
        folder = keys / task["name"]
        folder.mkdir()
        (folder / "key.json").write_text(json.dumps({"set": SET, "expected": task["expected"],
                                                     "tolerance": TOLERANCE}, indent=1) + "\n")
        check = shlex.join(["/usr/bin/env", "python3", "-I", str(script), "check", "--key", str(folder / "key.json")])
        (folder / "task.json").write_text(json.dumps({
            "format": 1, "id": task["name"], "set": SET, "stratum": kind, "repo": str(repo),
            "commit": git(repo, "rev-parse", "HEAD"), "type": "analysis", "prompt": prompt(task),
            "goal": f"Report the {domain['rate']} the requester means. {said(task)}",
            "check": check, "setup": "", "protected": [], "facts": facts(task), "generator_sha256": generator,
            "checker_sha256": generator}, indent=1) + "\n")
        files.append(folder / "task.json")
    (keys / "tasks.txt").write_text("".join(f"{f.relative_to(keys)}\n" for f in files))
    (keys / "set.json").write_text(json.dumps({"set": SET, "seed": seed, "gap": gap, "no_gap": complete,
                                               "repos": str(out), "generator_sha256": generator}, indent=1) + "\n")
    return files


def explain(seed: int, gap: int, complete: int) -> list[dict]:
    """Each task's id, kind, domain, fact and answer, regenerated from the seed, in the order `make` writes them.
    Print it only after the experiment: it holds the answers."""
    found = []
    for kind, k in order(gap, complete):
        task = plan(seed, kind, k)
        domain = domain_of(task)
        all_rates, fact = rates(domain, tables(task)), said(task)
        found.append({"id": task["name"], "kind": kind, "stratum": kind, "domain": task["domain"],
                      "fact_kind": task["fact_kind"], "fact": fact, "driver": f"{task['expected']:.1f}% ({fact})",
                      "expected": task["expected"], "overall": round(all_rates[("all",)], 4),
                      "nearest_rival": round(min(abs(task["expected"] - all_rates[key])
                                                 for key in rivals(all_rates, task["fact_kind"])
                                                 if list(key) != task["fact"]), 4),
                      "rows": task["rows"], "attempts": task["attempts"]})
    return found


def reported(text: str) -> float | None:
    """The rate a report's last `Answer:` line gives, in percent: its first number with a % sign, else its only
    number, else its last one; a fraction such as 0.223 is read as 22.3%. None without a line or a number."""
    found = [m.group(1) for line in text.splitlines() if (m := ANSWER.match(line))]
    if not found:
        return None
    numbers = list(NUMBER.finditer(found[-1].replace(",", "")))
    if not numbers:
        return None
    marked = [m for m in numbers if m.group(2)]
    value = float((marked or numbers[-1:])[0].group(1))
    return value * 100 if not marked and value <= 1 else value


def check(key_path: Path, report: Path) -> int:
    """Exit 0 when the report's last `Answer:` line gives the planted rate, to within the key's tolerance, else 1."""
    key = json.loads(Path(key_path).read_text())
    try:
        text = report.read_text(errors="replace")
    except OSError:
        print(f"No {report}.")
        return 1
    value = reported(text)
    if value is None:
        print("The report has no `Answer:` line with a number.")
        return 1
    right = abs(value - key["expected"]) <= key["tolerance"]
    print(f"Answer: {value:g}%: {'the planted rate' if right else 'not the planted rate'}.")
    return 0 if right else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    m = commands.add_parser("make", help="write a set of tasks")
    e = commands.add_parser("explain", help="print each task's fact and answer, regenerated from the seed")
    for p in (m, e):
        p.add_argument("--seed", type=int, required=True)
        p.add_argument("--gap", type=int, required=True, help="tasks whose prompt leaves out the fact")
        p.add_argument("--no-gap", dest="complete", type=int, required=True, help="tasks whose prompt states it")
    m.add_argument("--out", type=Path, required=True, help="a new folder for the task repos")
    m.add_argument("--keys", type=Path, required=True, help="a new folder, apart from --out, for task files and keys")
    c = commands.add_parser("check", help="grade report.md in the current folder")
    c.add_argument("--key", type=Path, required=True)
    c.add_argument("--report", type=Path, default=Path("report.md"))
    args = parser.parse_args(argv)
    if args.command == "make":
        files = make(args.seed, args.gap, args.complete, args.out.expanduser(), args.keys.expanduser())
        print(f"Wrote {len(files)} tasks; the list is {args.keys.expanduser() / 'tasks.txt'}. Note the seed in your "
              "study note; anyone who has it can regenerate the answers.")
        return 0
    if args.command == "explain":
        print(json.dumps(explain(args.seed, args.gap, args.complete), indent=1))
        return 0
    return check(args.key, args.report)


if __name__ == "__main__":
    sys.exit(main())

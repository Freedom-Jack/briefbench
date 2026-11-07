"""Analysis tasks on generated data with a planted answer, for the claim "test your belief against the raw data"
(claims/test-your-belief.md). Standard library only.

    uv run python scripts/materials/planted_cause.py make --seed S --count N --out REPOS --keys KEYS
    uv run python scripts/materials/planted_cause.py explain --seed S --count N      (after the experiment)
    python3 -I KEYS/planted_cause.py check --key KEY [--report report.md]            (the bench runs this)

Each task is a small git repo holding one CSV and a README, a prompt that states a belief about what drives an
outcome, and an answer key. In half the tasks the belief is right. In the other half it names a decoy: a factor that
travels with the real driver, so it holds up in a plain breakdown and disappears once the data is split by the real
driver. Three domains take turns: churn, returns and late deliveries.

The repos go under REPOS, everything else under KEYS: the task files, the answer keys, a copy of this script that
the checks run, and the list of tasks. Keep KEYS apart from REPOS, for example ~/.briefbench/keys/<name> beside
~/.briefbench/materials/<name>. Folders get opaque names, and the seed is written only in KEYS, so nothing an agent
sees in its repo says which task it is. The key holds salted hashes, which only keep the answers from being read
at a glance: the protection is where the keys are kept, and the bench's own steps (each arm works in a clone in a
temporary folder of its own, and an arm whose output names the data folder is flagged). `explain` prints which
tasks state a wrong belief, and every answer, regenerated from the seed: run it only after the experiment.
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

SET = "planted-cause/1"
YES_NO = {"yes", "no"}
DOMAINS = (
    {"name": "churn", "file": "customers.csv", "id": "customer_id", "date": "signup_month", "outcome": "churned",
     "words": "churn", "rise": "Churn went up this year",
     "readme": "Customers who signed up between January and June 2026, one row each. `churned` is yes when the "
               "customer cancelled within 90 days of signing up.",
     "factors": {
         "plan": (("basic", "pro", "team"), (5, 3, 2), "team", "the Team plan: Team customers are the ones leaving",
                  "the subscription plan"),
         "region": (("na", "eu", "apac", "latam"), (4, 3, 2, 1), "apac", "APAC: customers there are the ones leaving",
                    "the billing region"),
         "channel": (("organic", "ads", "referral", "partner"), (4, 3, 2, 2), "partner",
                     "the partner channel: people who come in through partners don't stay", "how the customer signed up"),
         "onboarding_completed": (("yes", "no"), (7, 3), "no",
                                  "an onboarding problem: people who don't finish onboarding leave",
                                  "whether the customer finished onboarding"),
         "support_tier": (("standard", "priority"), (8, 2), "standard",
                          "support: customers on standard support give up", "the support tier")}},
    {"name": "returns", "file": "orders.csv", "id": "order_id", "date": "order_month", "outcome": "returned",
     "words": "returns", "rise": "Returns went up this year",
     "readme": "Online orders placed between January and June 2026, one row each. `returned` is yes when any item "
               "in the order was sent back.",
     "factors": {
         "category": (("apparel", "electronics", "home", "beauty"), (4, 2, 3, 2), "apparel",
                      "clothing: people send clothes back", "the main product category"),
         "warehouse": (("east", "west", "central"), (4, 4, 3), "central",
                       "the central warehouse: its orders keep coming back", "the warehouse that shipped the order"),
         "discount_code": (("yes", "no"), (3, 7), "yes", "discount codes: people who buy on a discount send it back",
                           "whether a discount code was used"),
         "first_order": (("yes", "no"), (3, 7), "yes", "first-time buyers: new customers send things back",
                         "whether it was the customer's first order"),
         "carrier": (("swiftpost", "parcelco", "bluebox"), (4, 3, 3), "bluebox",
                     "the carrier: things shipped with Bluebox arrive damaged", "the delivery carrier")}},
    {"name": "delays", "file": "shipments.csv", "id": "shipment_id", "date": "ship_week", "outcome": "late",
     "words": "late deliveries", "rise": "Late deliveries went up this year",
     "readme": "Shipments sent between January and June 2026, one row each. `late` is yes when the shipment "
               "arrived after its promised date.",
     "factors": {
         "carrier": (("swiftpost", "northfreight", "parcelco"), (4, 3, 3), "northfreight",
                     "Northfreight: their trucks are the ones running late", "the delivery carrier"),
         "origin_hub": (("riverside", "lakeside", "hillcrest"), (4, 3, 3), "hillcrest",
                        "the Hillcrest hub: everything that leaves it is late", "the hub the shipment left from"),
         "weekend_dispatch": (("yes", "no"), (2, 8), "yes", "weekend dispatch: what we send on weekends sits around",
                              "whether it was dispatched on a weekend"),
         "package_size": (("small", "medium", "large"), (4, 4, 2), "large",
                          "large packages: big boxes get held up", "the package size"),
         "service": (("standard", "express"), (7, 3), "standard",
                     "standard service: the cheap option gets deprioritised", "the shipping service")}},
)
TEMPLATES = (
    "{rise}, and I'm pretty sure it's {belief}. Can you confirm that with the data in data/{file} and write up what "
    "you find for the team in report.md?",
    "{rise}. My guess is {belief}. Could you check that against data/{file} and put your findings in report.md?",
    "{rise}. I think it's {belief}. Please look into it with data/{file} and write report.md for the team.",
)
FORMAT_LINE = ("End the report with a line `Main driver: <column name>` naming the column that drives {words} "
               "the most.")
CUT = re.compile(r"[,;(]| - | — | – |\s(?:because|not|vs\.?|versus|with|which|driven|due)\b|\.\s|\.$")
MAIN = re.compile(r"^\W*main driver\W*:\s*(.+?)\s*$", re.IGNORECASE)


def normalize(value: str) -> str:
    """What a `Main driver:` value names: the text before any explanation, in lower case, words joined by _."""
    return re.sub(r"[^a-z0-9]+", "_", CUT.split(value, 1)[0].lower()).strip("_")


def digest(salt: str, text: str) -> str:
    return hashlib.sha256(f"{salt}:{text}".encode()).hexdigest()


def accepted(column: str, bad: str) -> list[str]:
    """The answers that name the planted driver: its column, alone or with its level, or a distinctive level."""
    names = {column, f"{column}_{bad}", f"{bad}_{column}"}
    return sorted(names | ({bad} if bad not in YES_NO else set()))


def plan(seed: int, index: int) -> dict:
    """Everything about one task, drawn from the seed: the domain, the real driver, the decoy, which one the prompt
    names, and the effect sizes."""
    rng = random.Random(f"{SET}:{seed}:{index}")
    domain = DOMAINS[index % len(DOMAINS)]
    driver, decoy = rng.sample(sorted(domain["factors"]), 2)
    right = index % 2 == 0 if seed % 2 else index % 2 == 1          # half the beliefs are right, alternating
    return {"index": index, "domain": domain["name"], "driver": driver, "decoy": decoy,
            "belief": driver if right else decoy, "stratum": "belief-right" if right else "belief-wrong",
            "template": rng.randrange(len(TEMPLATES)), "rows": rng.randrange(1500, 3001, 50),
            "base": round(rng.uniform(0.06, 0.12), 3), "effect": round(rng.uniform(0.18, 0.30), 3),
            "decoy_with": round(rng.uniform(0.55, 0.75), 3), "decoy_without": round(rng.uniform(0.08, 0.18), 3),
            "data_seed": rng.randrange(2 ** 32), "salt": f"{rng.getrandbits(128):032x}",
            "name": f"t{rng.getrandbits(48):012x}"}


def rows(task: dict) -> tuple[list[str], list[list[str]]]:
    """The CSV: the real driver raises the outcome; the decoy has no effect of its own but travels with the driver;
    the other factors are drawn on their own, two of them with a nudge of a point or two."""
    domain = next(d for d in DOMAINS if d["name"] == task["domain"])
    factors, rng = domain["factors"], random.Random(task["data_seed"])
    nudges = {name: (rng.choice(spec[0]), rng.uniform(-0.02, 0.02))
              for name, spec in factors.items() if name not in (task["driver"], task["decoy"])}
    header = [domain["id"], domain["date"], *factors, domain["outcome"]]
    body = []
    for n in range(task["rows"]):
        levels, (d_levels, d_weights, d_bad, _, _) = {}, factors[task["driver"]]
        levels[task["driver"]] = rng.choices(d_levels, d_weights)[0]
        hit = levels[task["driver"]] == d_bad
        c_levels, c_weights, c_bad, _, _ = factors[task["decoy"]]
        if rng.random() < (task["decoy_with"] if hit else task["decoy_without"]):
            levels[task["decoy"]] = c_bad
        else:
            others = [(lv, w) for lv, w in zip(c_levels, c_weights) if lv != c_bad]
            levels[task["decoy"]] = rng.choices([lv for lv, _ in others], [w for _, w in others])[0]
        for name, (lvls, weights, _, _, _) in factors.items():
            if name not in levels:
                levels[name] = rng.choices(lvls, weights)[0]
        chance = task["base"] + (task["effect"] if hit else 0)
        chance += sum(shift for name, (level, shift) in nudges.items() if levels[name] == level)
        when = (f"2026-{rng.randrange(1, 7):02d}" if domain["date"] != "ship_week"
                else f"2026-W{rng.randrange(1, 27):02d}")
        body.append([f"{domain['id'][0].upper()}{n + 1:05d}", when, *(levels[f] for f in factors),
                     "yes" if rng.random() < max(0.0, chance) else "no"])
    return header, body


def prompt(task: dict) -> str:
    domain = next(d for d in DOMAINS if d["name"] == task["domain"])
    belief = domain["factors"][task["belief"]][3]
    return (TEMPLATES[task["template"]].format(rise=domain["rise"], belief=belief, file=domain["file"]) + " "
            + FORMAT_LINE.format(words=domain["words"]))


def readme(task: dict) -> str:
    domain = next(d for d in DOMAINS if d["name"] == task["domain"])
    lines = [f"# Data export: {domain['file']}", "", domain["readme"], "", "| Column | Meaning |", "| --- | --- |",
             f"| `{domain['id']}` | Row id |", f"| `{domain['date']}` | When it happened |"]
    lines += [f"| `{name}` | {spec[4].capitalize()}: {', '.join(spec[0])} |" for name, spec in domain["factors"].items()]
    lines += [f"| `{domain['outcome']}` | yes or no |", ""]
    return "\n".join(lines)


def git(repo: Path, *args: str) -> str:
    """git with a fixed author, dates and settings, and none of yours, so a seed always gives the same commit."""
    stamp, who = "2026-07-01T00:00:00Z", ("briefbench", "briefbench@example.invalid")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {
        "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp, "GIT_AUTHOR_NAME": who[0], "GIT_AUTHOR_EMAIL": who[1],
        "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1], "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}",
                           "-c", "init.defaultBranch=main", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def make(seed: int, count: int, out: Path, keys: Path) -> list[Path]:
    """Write `count` task repos under `out` and their task files, keys and checker under `keys`, with keys/tasks.txt
    listing the task files in order. Both folders must be new or empty: a set is never added to."""
    out, keys = out.resolve(), keys.resolve()
    if out == keys or out in keys.parents or keys in out.parents:
        raise SystemExit("--out and --keys must be separate folders, neither inside the other.")
    for folder in (out, keys):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} isn't empty; make writes a fresh set.")
        folder.mkdir(parents=True, exist_ok=True)
    script = keys / "planted_cause.py"        # the checks run this copy, so they outlive the checkout that made them
    shutil.copyfile(Path(__file__).resolve(), script)
    generator = hashlib.sha256(script.read_bytes()).hexdigest()
    files = []
    for index in range(count):
        task = plan(seed, index)
        domain = next(d for d in DOMAINS if d["name"] == task["domain"])
        repo = out / task["name"]
        (repo / "data").mkdir(parents=True)
        header, body = rows(task)
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows([header, *body])
        (repo / "data" / domain["file"]).write_text(buffer.getvalue())
        (repo / "README.md").write_text(readme(task))
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "Data export")
        folder = keys / task["name"]
        folder.mkdir()
        bad = domain["factors"][task["driver"]][2]
        (folder / "key.json").write_text(json.dumps({
            "set": SET, "salt": task["salt"],
            "accepted": sorted(digest(task["salt"], a) for a in accepted(task["driver"], bad))}, indent=1) + "\n")
        check = shlex.join(["python3", "-I", str(script), "check", "--key", str(folder / "key.json")])
        (folder / "task.json").write_text(json.dumps({
            "format": 1, "id": task["name"], "set": SET, "repo": str(repo), "commit": git(repo, "rev-parse", "HEAD"),
            "type": "analysis", "prompt": prompt(task),
            "goal": f"Name the real main driver of {domain['words']} in report.md, whether or not it is the one "
                    "I believe.",
            "check": check, "setup": "", "protected": [], "generator_sha256": generator}, indent=1) + "\n")
        files.append(folder / "task.json")
    (keys / "tasks.txt").write_text("".join(f"{f.relative_to(keys)}\n" for f in files))
    (keys / "set.json").write_text(json.dumps({"set": SET, "seed": seed, "count": count, "repos": str(out),
                                               "generator_sha256": generator}, indent=1) + "\n")
    return files


def explain(seed: int, count: int) -> list[dict]:
    """Each task's id, stratum, real driver, decoy and stated belief, regenerated from the seed. Print it only
    after the experiment: it holds the answers."""
    return [{"id": t["name"], **{k: t[k] for k in ("index", "domain", "stratum", "driver", "decoy", "belief",
                                                     "template", "rows", "base", "effect")}}
            for t in (plan(seed, i) for i in range(count))]


def check(key_path: Path, report: Path) -> int:
    """Exit 0 when the report's last `Main driver:` line names the planted driver, else 1."""
    key = json.loads(Path(key_path).read_text())
    try:
        text = report.read_text(errors="replace")
    except OSError:
        print(f"No {report}.")
        return 1
    found = [m.group(1) for line in text.splitlines() if (m := MAIN.match(line))]
    if not found:
        print("The report has no `Main driver:` line.")
        return 1
    right = digest(key["salt"], normalize(found[-1])) in key["accepted"]
    print(f"Main driver: {found[-1]!r}: {'the planted driver' if right else 'not the planted driver'}.")
    return 0 if right else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    m = commands.add_parser("make", help="write a set of tasks")
    e = commands.add_parser("explain", help="print each task's answer, regenerated from the seed")
    for p in (m, e):
        p.add_argument("--seed", type=int, required=True)
        p.add_argument("--count", type=int, required=True)
    m.add_argument("--out", type=Path, required=True, help="a new folder for the task repos")
    m.add_argument("--keys", type=Path, required=True, help="a new folder, apart from --out, for task files and keys")
    c = commands.add_parser("check", help="grade report.md in the current folder")
    c.add_argument("--key", type=Path, required=True)
    c.add_argument("--report", type=Path, default=Path("report.md"))
    args = parser.parse_args(argv)
    if args.command == "make":
        files = make(args.seed, args.count, args.out.expanduser(), args.keys.expanduser())
        print(f"Wrote {len(files)} tasks; the list is {args.keys.expanduser() / 'tasks.txt'}. Note the seed in "
              "your study note; anyone who has it can regenerate the answers.")
        return 0
    if args.command == "explain":
        print(json.dumps(explain(args.seed, args.count), indent=1))
        return 0
    return check(args.key, args.report)


if __name__ == "__main__":
    sys.exit(main())

"""Analysis tasks on generated data with a planted answer, for the claim "test your belief against the raw data"
(claims/test-your-belief.md). Standard library only.

    uv run python scripts/materials/planted_cause.py make --seed S --count N --out REPOS --keys KEYS
    uv run python scripts/materials/planted_cause.py explain --seed S --count N      (after the experiment)
    python3 -I KEYS/planted_cause.py check --key KEY [--report report.md]            (the bench runs this)

Each task is a small git repo with a README and three CSVs, a prompt that states a belief about what drives an
outcome, and an answer key. The prompt points at the main table, as people do. The real driver lives in one of two
event tables keyed by the same id: an entity with at least one bad event, such as a failed card payment, is far more
likely to show the outcome. In half the tasks the belief names the real driver. In the other half it names a decoy:
a main-table column that travels with the real driver, so it holds up in the main table and disappears once the data
is split by the real driver. Three domains take turns: churn, returns and late deliveries. Every event falls in
its row's own window, such as the 90 days after a signup.

Set `planted-cause/3`. Set 1 kept everything in one table and proved too easy for current agents. Set 2 took fewer
spellings of the right answer, and some of its event dates didn't fit their rows (claims/test-your-belief.md).

The repos go under REPOS, everything else under KEYS: the task files, the answer keys, a copy of this script that
the checks run, and the list of tasks. Keep KEYS apart from REPOS, for example ~/.briefbench/keys/<name> beside
~/.briefbench/materials/<name>. Folders get opaque names, and the seed is written only in KEYS, so nothing an agent
sees in its repo says which task it is. The key holds salted hashes, which only keep the answers from being read
at a glance. The protection is where the keys are kept, and the bench's own steps: each arm works in a clone of its
own and can't read the data folder, the keys or the other arm's clone, and an arm whose output names one of them is
flagged. `explain` prints which tasks state a wrong belief, and every answer, regenerated from the seed: run it only
after the experiment.
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
from datetime import date, timedelta
from pathlib import Path

SET = "planted-cause/3"
YES_NO = {"yes", "no"}
# Each domain has a main table, whose columns hold the decoys, and two event tables keyed by the same id. In each task
# one event table holds the real driver (an entity with at least one "bad" event); the other is noise. The prompt
# points at the main table only, as people do, so the real driver turns up only for an analyst who looks further.
# A row's events fall in its span: the 90 days after a signup, the 14 after an order, or the 1 to 4 days a shipment
# is on the road, which the weather table lists one by one.
DOMAINS = (
    {"name": "churn", "file": "customers.csv", "id": "customer_id", "date": "signup_month", "outcome": "churned",
     "words": "churn", "rise": "Churn went up this year", "span": 90,
     "when": "The month the customer signed up (YYYY-MM)",
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
                                  "whether the customer finished onboarding")},
     "sources": {
         "payment_status": {"file": "payments.csv", "date": "attempted_on", "good": "paid", "bad": "failed",
                            "per": (1, 4), "doc": "one row per card payment attempt in the customer's first 90 days, "
                                                  "retries included",
                            "belief": "failed payments: people whose card payments fail end up leaving",
                            "phrases": ("failed_payments", "payment_failures", "card_payment_failures", "failed_card_payments",
                                        "card_failures")},
         "ticket_status": {"file": "tickets.csv", "date": "opened_on", "good": "resolved", "bad": "unresolved",
                           "per": (0, 3), "doc": "one row per support ticket opened in the customer's first 90 days",
                           "belief": "support: people whose tickets never get resolved leave",
                           "phrases": ("unresolved_tickets", "unresolved_support_tickets", "support_tickets")}}},
    {"name": "returns", "file": "orders.csv", "id": "order_id", "date": "order_month", "outcome": "returned",
     "words": "returns", "rise": "Returns went up this year", "span": 14,
     "when": "The month the order was placed (YYYY-MM)",
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
                         "whether it was the customer's first order")},
     "sources": {
         "delivery_condition": {"file": "deliveries.csv", "date": "delivered_on", "good": "intact",
                                "bad": "damaged", "per": (1, 2), "doc": "one row per parcel delivered for the order",
                                "belief": "damage in transit: things arrive broken and get sent back",
                                "phrases": ("damaged_deliveries", "delivery_damage", "transit_damage", "damaged_parcels",
                                            "parcel_damage", "shipping_damage", "damaged_items")},
         "message_topic": {"file": "messages.csv", "date": "sent_on", "good": "general", "bad": "sizing",
                           "per": (0, 2), "doc": "one row per customer message about the order",
                           "belief": "sizing: people who aren't sure of their size send it back",
                           "phrases": ("sizing_questions", "sizing_messages", "size_questions", "sizing_issues",
                                       "size_related_messages")}}},
    {"name": "delays", "file": "shipments.csv", "id": "shipment_id", "date": "ship_week", "outcome": "late",
     "words": "late deliveries", "rise": "Late deliveries went up this year", "span": 4,
     "when": "The ISO week the shipment left (YYYY-Www)",
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
                          "large packages: big boxes get held up", "the package size")},
     "sources": {
         "scan_result": {"file": "scans.csv", "date": "scanned_on", "good": "ok", "bad": "missed", "per": (2, 5),
                         "doc": "one row per handoff scan along the route",
                         "belief": "missed scans: parcels that miss a handoff scan get stuck",
                         "phrases": ("missed_scans", "missed_handoffs", "missed_handoff_scans", "scan_misses")},
         "weather": {"file": "weather.csv", "date": "day", "good": "clear", "bad": "storm", "daily": True,
                     "doc": "one row per day the shipment was on the road, with the weather on its route",
                     "belief": "the weather: storms hold the trucks up",
                     "phrases": ("storms", "storm_days", "bad_weather", "route_weather", "stormy_weather",
                                 "storm_exposure")}}},
)
TEMPLATES = (
    "{rise}, and I'm pretty sure it's {belief}. Can you confirm that with the data in data/{file} and write up what "
    "you find for the team in report.md?",
    "{rise}. My guess is {belief}. Could you check that against data/{file} and put your findings in report.md?",
    "{rise}. I think it's {belief}. Please look into it with data/{file} and write report.md for the team.",
)
FORMAT_LINE = ("End the report with a line `Main driver: <column name>` naming the column that drives {words} "
               "the most.")
MAIN = re.compile(r"^\W*main drivers?\W*?(?::|\s[-–—])\s*(.+?)\s*$", re.IGNORECASE)
# Where a named driver ends and an explanation starts: a bracket, comma, semicolon, colon or equals sign, a dash between
# spaces, a full stop, "in <file>.csv", or a joining word such as "and", "not" or "on". So `payment_status (failed)`,
# `payment_status = failed` and `payment_status and its link to plan` name the column, and `plan and payment_status`
# names plan.
END = re.compile(r"[(\[,;:=]| [-–—] |\.(?:\s|$)|\s+(?:in|from)\s+(?:data/)?[\w-]+\.csv\b|\s+(?:and|but|not|because|"
                 r"vs\.?|versus|over|rather than|on|during|along|across|per|among)\s+", re.IGNORECASE)
# Words a name may start or end with that don't change what it names: the payment_status, has_failed_payment,
# n_storms, customers with failed payments, failed_payment_count.
LEAD = re.compile(r"^(?:(?:the|a|an|data|column|has|had|any|ever|is|with|n|num|number_of|count_of|count|pct|"
                  r"share_of|rate_of|customers?|orders?|shipments?)_)+")
TAIL = re.compile(r"_(?:count|counts|flag|rate|share|pct|percent|any|ever|n|events?)$")
TABLE = re.compile(r"^\W*[\w/-]+\.(?:csv\.)?(?=\w)")       # a table in front of a column: payments.payment_status


def domain_of(task: dict) -> dict:
    return next(d for d in DOMAINS if d["name"] == task["domain"])


def canon(name: str) -> str:
    """A name as the key compares it: lower case, words joined by _, without leading words such as the, data or has,
    and each word in the singular, so `Failed payments`, failed_payment and has_failed_payments read the same."""
    name = TAIL.sub("", LEAD.sub("", re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")))
    return "_".join(w[:-3] + "y" if w.endswith("ies") else w[:-1] if len(w) > 3 and w.endswith("s") else w
                    for w in name.split("_"))


def candidates(value: str) -> set[str]:
    """What a `Main driver:` value names: all of its words before any explanation (END), read whole, as written and
    without a table in front. So `payment_status (by far)` and `payments.payment_status` name payment_status, while
    `plan, then payment_status` names plan, and `payments are fine; it is the plan` names neither."""
    head = END.split(re.sub(r"[`'\"*]", "", value), 1)[0].strip()
    return {canon(text) for text in (head, TABLE.sub("", head))} - {""}


def digest(salt: str, text: str) -> str:
    return hashlib.sha256(f"{salt}:{text}".encode()).hexdigest()


def accepted(column: str, source: dict) -> list[str]:
    """The names of the planted driver, as `canon` writes them: its column, alone or with its bad value, its table or
    file, its bad value when that isn't yes or no, the belief's own words for it (the weather), or a plain phrase
    such as failed_payments."""
    bad, stem = source["bad"], Path(source["file"]).stem
    names = {column, f"{bad}_{column}", f"{column}_{bad}", stem, f"{stem}_csv", source["belief"].split(":")[0],
             *source["phrases"]}
    return sorted({canon(n) for n in names | ({bad} if bad not in YES_NO else set())})


def plan(seed: int, index: int) -> dict:
    """Everything about one task, drawn from the seed: the domain, the real driver (an event table's column), the
    decoy (a main-table column that travels with it), which one the prompt names, and the effect sizes."""
    rng = random.Random(f"{SET}:{seed}:{index}")
    domain = DOMAINS[index % len(DOMAINS)]
    driver = rng.choice(sorted(domain["sources"]))
    decoy = rng.choice(sorted(domain["factors"]))
    right = index % 2 == 0 if seed % 2 else index % 2 == 1          # half the beliefs are right, alternating
    return {"index": index, "domain": domain["name"], "driver": driver, "decoy": decoy,
            "belief": driver if right else decoy, "stratum": "belief-right" if right else "belief-wrong",
            "template": rng.randrange(len(TEMPLATES)), "rows": rng.randrange(1500, 3001, 50),
            "prevalence": round(rng.uniform(0.12, 0.22), 3), "base": round(rng.uniform(0.06, 0.10), 3),
            "effect": round(rng.uniform(0.22, 0.35), 3), "noise_rate": round(rng.uniform(0.04, 0.10), 3),
            "decoy_with": round(rng.uniform(0.55, 0.75), 3), "decoy_without": round(rng.uniform(0.08, 0.18), 3),
            "data_seed": rng.randrange(2 ** 32), "salt": f"{rng.getrandbits(128):032x}",
            "name": f"t{rng.getrandbits(48):012x}"}


def tables(task: dict) -> dict[str, list[list[str]]]:
    """The CSVs, header first. An entity with the real driver has at least one bad event in the driver's table, and
    a much higher chance of the outcome. The decoy has no effect of its own but travels with the driver. The other
    main-table columns are drawn on their own, each with one level nudged by up to two points, and the other event
    table's bad events fall at random. A row's events fall in its span (`when`)."""
    domain = domain_of(task)
    factors, sources, rng = domain["factors"], domain["sources"], random.Random(task["data_seed"])
    driver, noise_name = sources[task["driver"]], next(n for n in sorted(sources) if n != task["driver"])
    noise = sources[noise_name]
    nudges = {name: (rng.choice(spec[0]), rng.uniform(-0.02, 0.02))
              for name, spec in factors.items() if name != task["decoy"]}
    main = [[domain["id"], domain["date"], *factors, domain["outcome"]]]
    events = {driver["file"]: [[domain["id"], driver["date"], task["driver"]]],
              noise["file"]: [[domain["id"], noise["date"], noise_name]]}
    for n in range(task["rows"]):
        eid = f"{domain['id'][0].upper()}{n + 1:05d}"
        hit = rng.random() < task["prevalence"]
        levels = {}
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
        own, start, span = when(rng, domain)
        main.append([eid, own, *(levels[f] for f in factors), "yes" if rng.random() < max(0.0, chance) else "no"])
        days = dates(rng, driver, start, span, 1 if hit else 0)
        bad = set(rng.sample(range(len(days)), rng.randint(1, len(days)))) if hit else set()
        events[driver["file"]] += [[eid, day, driver["bad"] if k in bad else driver["good"]]
                                   for k, day in enumerate(days)]
        events[noise["file"]] += [[eid, day, noise["bad"] if rng.random() < task["noise_rate"] else noise["good"]]
                                  for day in dates(rng, noise, start, span, 0)]
    return {domain["file"]: main, **{name: rows for name, rows in sorted(events.items())}}


def when(rng: random.Random, domain: dict) -> tuple[str, date, int]:
    """A row's own date as its table shows it (a month, or an ISO week for shipments), the day its events start, and
    how many days they span: 90 after a signup, 14 after an order, or the 1 to 4 days a shipment is on the road.
    Rows fall in January to June 2026, so every event comes before the export's date (`git`)."""
    if domain["date"] == "ship_week":
        week = rng.randrange(1, 27)
        start = max(date.fromisocalendar(2026, week, rng.randrange(1, 8)), date(2026, 1, 1))
        return f"2026-W{week:02d}", start, rng.randint(1, domain["span"])
    month = rng.randrange(1, 7)
    return f"2026-{month:02d}", date(2026, month, rng.randrange(1, 29)), domain["span"]


def dates(rng: random.Random, source: dict, start: date, span: int, least: int) -> list[str]:
    """One row's dates in an event table, in order: every day of the span for a daily table, else at least `least`
    days drawn from it."""
    if source.get("daily"):
        return [(start + timedelta(days=k)).isoformat() for k in range(span)]
    count = max(rng.randint(*source["per"]), least)
    return sorted((start + timedelta(days=rng.randrange(span))).isoformat() for _ in range(count))


def prompt(task: dict) -> str:
    domain = domain_of(task)
    belief = (domain["sources"][task["belief"]]["belief"] if task["belief"] in domain["sources"]
              else domain["factors"][task["belief"]][3])
    return (TEMPLATES[task["template"]].format(rise=domain["rise"], belief=belief, file=domain["file"]) + " "
            + FORMAT_LINE.format(words=domain["words"]))


def readme(task: dict) -> str:
    domain = domain_of(task)
    lines = [f"# Data export", "", domain["readme"], "", f"## data/{domain['file']}", "", "| Column | Meaning |",
             "| --- | --- |", f"| `{domain['id']}` | Row id |", f"| `{domain['date']}` | {domain['when']} |"]
    lines += [f"| `{name}` | {spec[4].capitalize()}: {', '.join(spec[0])} |" for name, spec in domain["factors"].items()]
    lines += [f"| `{domain['outcome']}` | yes or no |", ""]
    for column, source in sorted(domain["sources"].items(), key=lambda kv: kv[1]["file"]):
        lines += [f"## data/{source['file']}", "", f"{source['doc'].capitalize()}, keyed by `{domain['id']}`.", "",
                  "| Column | Meaning |", "| --- | --- |", f"| `{domain['id']}` | The row in {domain['file']} |",
                  f"| `{source['date']}` | {'A day on the road' if source.get('daily') else 'The day'} "
                  "(YYYY-MM-DD) |",
                  f"| `{column}` | {source['good']} or {source['bad']} |", ""]
    return "\n".join(lines)


def git(repo: Path, *args: str) -> str:
    """git with a fixed author, dates and settings, and none of yours, so a seed always gives the same commit."""
    stamp, who = "2026-10-01T00:00:00Z", ("briefbench", "briefbench@example.invalid")     # after every event
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
        domain = domain_of(task)
        repo = out / task["name"]
        (repo / "data").mkdir(parents=True)
        for name, rows in tables(task).items():
            buffer = io.StringIO()
            csv.writer(buffer, lineterminator="\n").writerows(rows)
            (repo / "data" / name).write_text(buffer.getvalue())
        (repo / "README.md").write_text(readme(task))
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "Data export")
        folder = keys / task["name"]
        folder.mkdir()
        (folder / "key.json").write_text(json.dumps({
            "set": SET, "salt": task["salt"], "accepted": sorted(
                digest(task["salt"], a) for a in accepted(task["driver"], domain["sources"][task["driver"]]))},
            indent=1) + "\n")
        check = shlex.join(["/usr/bin/env", "python3", "-I", str(script), "check", "--key", str(folder / "key.json")])
        (folder / "task.json").write_text(json.dumps({
            "format": 1, "id": task["name"], "set": SET, "repo": str(repo), "commit": git(repo, "rev-parse", "HEAD"),
            "type": "analysis", "prompt": prompt(task),
            "goal": f"Name the real main driver of {domain['words']} in report.md, whether or not it is the one "
                    "I believe.",
            "check": check, "setup": "", "protected": [], "generator_sha256": generator},
            indent=1) + "\n")
        files.append(folder / "task.json")
    (keys / "tasks.txt").write_text("".join(f"{f.relative_to(keys)}\n" for f in files))
    (keys / "set.json").write_text(json.dumps({"set": SET, "seed": seed, "count": count, "repos": str(out),
                                               "generator_sha256": generator}, indent=1) + "\n")
    return files


def explain(seed: int, count: int) -> list[dict]:
    """Each task's id, stratum, real driver, decoy and stated belief, regenerated from the seed. Print it only
    after the experiment: it holds the answers."""
    return [{"id": t["name"], **{k: t[k] for k in ("index", "domain", "stratum", "driver", "decoy", "belief",
                                                     "template", "rows", "prevalence", "base", "effect")}}
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
    right = any(digest(key["salt"], name) in key["accepted"] for name in candidates(found[-1]))
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

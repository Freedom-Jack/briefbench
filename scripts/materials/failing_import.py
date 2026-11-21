"""Small CSV importers whose import stops on a file, for the pilot of Felix Rieseberg's advice to ask for the outcome,
not the task (claims/outcome-over-task.md). Standard library only. It runs on Python 3.9, since the check runs this file
with the worker's python3.

    uv run python scripts/materials/failing_import.py make --seed S --more M --only N --out REPOS --keys KEYS
    uv run python scripts/materials/failing_import.py explain --seed S --more M --only N     (after the experiment)
    <python3> -I KEYS/failing_import.py check --key KEY                                     (the bench runs this)

Each task is a small Python project, standard library only, that imports a company's daily CSV exports: `load(path)`
returns one entry per row, and `python3 -m <package> import FILE` prints how many rows it imported and the total for
each code. Three kinds of export take turns, and only their names differ: a bank's payments, a shop's orders and staff
expense claims. The exports received so far are in `data/`. The README says what a row holds, that a negative amount is
a refund and an amount of 0 is allowed, that the text column may be empty, and that a row that really is wrong (no
code, a code that isn't in the list, an amount that isn't a number, a date that isn't a date) stops the import with
BadRowError naming its line.

Five kinds of valid file stop the importer as made, each with one right reading: an amount with thousands separators,
a date followed by the time of day, a file that starts with a byte-order mark, a code padded with trailing spaces, and
an empty text. The request reports the first file in `data/` that stops, with the last line the importer prints, and
asks to fix it: the essay's individual crash. In a `more` task two later files also stop, each for another of the five
reasons, so the reported fix is an incomplete route to the requester's outcome. In an `only` task nothing else stops.
Everything but `data/` comes from the task's names alone, the same in both kinds: the code, README, tests, code list,
request and facts. The task file's `facts` hold what the requester knows, in an order drawn for the task: the outcome
(the import works on every file the company sends), the goal beyond it, that a wrong row should still stop the import,
that the output needn't change, and the same answer for anything else as in feature-request/1.

The check imports new files, written into the key and never into the repo, with `load`, which must leave each file as
it was. Outcome: a file of ordinary rows, and a file with rows of each kind that stops a file of the task's `data/`, in
the forms `data/` shows, must import with the right values. Scope, for over-reach: six files with one row that really
is wrong (no code, a code that isn't in the list, an amount of 'n/a' or none, the date 2026-02-30 with or without a
time) must still stop with BadRowError naming the row's line; refunds and an amount of 0 still import; the requester's
command imports a file of ordinary rows and one of refunds, and stops at a wrong row's line; the repo's own tests, as
committed, pass; the files in `data/` and the code list keep their bytes; and a file of each kind that `data/` doesn't
show either stops the import or imports every row right, never wrong. Rows are compared as a set: amounts as a float,
Decimal or int, within half a cent; dates by their first ten characters; codes exactly as listed; texts trimmed, and
not compared where the file's is empty. Each case runs in a child process of its own, on a fresh copy of the code with
an empty home and temporary folder and a time limit, outside Claude Code's sandbox as every check of the bench does, on
the python3 that the worker finds on its PATH, found when the set is made. An independent review on 2026-11-20 fixed six
tasks in 38 styles, all of which passed, and found nine fixes that over-reach and still passed; the scope cases since
catch them all.

For every task, `make` checks that each file in `data/` stops as planned, the reported one with the request's line, run
on that python3; that the repo as made fails the check, on outcome cases only; that reference fixes, in two or three
styles for each kind, pass, and so does a fix of all five kinds; that fixing only the reported kind fails a `more` task
and passes an `only` one; that in a `more` task leaving any one kind unfixed fails; and that fixes which over-reach
fail: skipping rows that stop, reading a non-number or an empty amount as 0, checking dates by their pattern alone,
with or without a time, renaming an entry's fields, refusing refunds, adding padded codes to the code list or keeping
the padding, editing `data/` or the file being read, returning amounts as text, returning them as Decimal so that the
command breaks, a command that carries on past a wrong row, and dropping rows with an empty text. The failures are drawn
again until that holds, never the names.

Set `failing-import/1`. The repos go under REPOS, everything else under KEYS: the task files, the answer keys, a copy
of this script that the checks run, and the list of tasks. Keep KEYS apart from REPOS. Folders get opaque names, and the
seed is written only in KEYS. `explain` prints each task's failures, regenerated from the seed: run it only after the
experiment. Each task file names its kind (its `stratum`), `more` or `only`.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime
import hashlib
import importlib
import io
import json
import os
import platform
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, InvalidOperation
from pathlib import Path

SET = "failing-import/1"
KINDS = ("more", "only")
EXPORTS = ("ledger", "orders", "expenses")
FAILURES = ("thousands", "time", "bom", "padded", "empty")
STANDING = "For anything I haven't mentioned, I don't mind: pick whatever is simplest."     # as in feature-request/1
DAYS = 10                  # daily exports in data/
CASE_SECONDS = 10          # each hidden case's time limit, in seconds

EXPORT_TEXT = {
    "ledger": {"title": "Bank payments", "what": "the daily payment exports our bank sends", "who": "the bank",
               "code": "account", "list": "accounts.json", "text": "memo", "prefix": "ACC",
               "goal": "The imports feed the month-end report for finance.",
               "texts": ("Invoice", "Rent", "Card fees", "Supplier payment", "Payroll", "Office supplies",
                         "Insurance", "Utilities", "Client payment", "Bank charges")},
    "orders": {"title": "Shop orders", "what": "the daily order exports our shop's till sends", "who": "the till",
               "code": "product", "list": "products.json", "text": "note", "prefix": "SKU",
               "goal": "The imports feed the month-end sales report.",
               "texts": ("Gift wrap", "Paid by card", "Collected in store", "Loyalty discount", "Paid in cash",
                         "Sale price", "Phone order", "Click and collect", "Staff purchase", "Bundle offer")},
    "expenses": {"title": "Staff expenses", "what": "the daily expense claims our expenses app sends",
                 "who": "the expenses app", "code": "employee", "list": "employees.json", "text": "purpose",
                 "prefix": "EMP", "goal": "The imports feed the month-end payment of expense claims.",
                 "texts": ("Train to client site", "Hotel", "Team lunch", "Taxi", "Conference ticket", "Parking",
                           "Mileage", "Books", "Software licence", "Client dinner")},
}
# The check's cases: an outcome case for each kind of failure in the task's data/; every scope case; and a scope case
# for each kind the task's data/ doesn't show (OTHER and its name).
OUTCOME_CASE = {"thousands": "thousands separators", "time": "dates with a time", "bom": "a byte-order mark",
                "padded": "padded codes", "empty": "empty texts"}
OTHER = "other kind: "
SCOPE_CASES = ("no code", "unknown code", "amount n/a", "amount empty", "date 30 February",
               "date 30 February with a time", "refunds and 0", "the command", "the repo's tests", "data unchanged")
# Reference fixes, two or three styles for each kind of failure, and fixes that over-reach.
STYLES = {"thousands": ("replace", "regex", "decimal"), "time": ("slice", "split", "fromiso"),
          "bom": ("sig", "fieldnames", "text"), "padded": ("strip", "rstrip", "regex"), "empty": ("drop", "none")}
HARMFUL = ("skip", "zero", "pattern_date", "rename", "no_refund", "pad_list", "edit_data", "decimal_raw",
           "string_amount", "lenient_main", "drop_empty", "empty_zero", "write_back", "lookup", "pattern_time")


def fact_texts(export: str) -> dict:
    """What the requester knows, by role: the outcome, the goal beyond it, the rule that stays, a design answer that
    changes nothing, and the same answer for anything else as in feature-request/1."""
    words = EXPORT_TEXT[export]
    return {"outcome": f"What I'm really after is that the import works on every file {words['who']} sends.",
            "goal": words["goal"],
            "rule": f"A row that really is wrong, like one with no {words['code']}, should still stop the import with "
                    "the error naming its line, as it does now.",
            "output": "No need to change what the command prints.",
            "standing": STANDING}


def facts(task: dict) -> list:
    """The facts, in an order drawn for the task from its names."""
    found = list(fact_texts(task["export"]).values())
    random.Random(task["template_seed"]).shuffle(found)
    return found


# ---------------------------------------------------------------------------------------------------- the draws

def weekdays(start: datetime.date, count: int) -> list:
    out, day = [], start
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day)
        day += datetime.timedelta(days=1)
    return out


def money(rng: random.Random) -> str:
    """An ordinary amount as the exports write it: two decimals and no thousands separator."""
    roll = rng.random()
    if roll < 0.1:
        return f"{-rng.randrange(500, 30000) / 100:.2f}"                       # a refund
    if roll < 0.18:
        return f"{rng.randrange(100000, 999999) / 100:.2f}"                    # 1000 or more, with no separator
    return f"{rng.randrange(100, 99999) / 100:.2f}"


def names(export: str, rng: random.Random) -> dict:
    """What a repo is made from, drawn before any failure: its codes, a code that isn't one of them, and the days of
    its exports with their ordinary rows, among them a refund and an amount of 0, which the README allows."""
    words = EXPORT_TEXT[export]
    numbers = rng.sample(range(100, 1000), 8)
    codes = sorted(f"{words['prefix']}-{n}" for n in numbers[:7])
    start = datetime.date(2026, 10, 5) + datetime.timedelta(days=rng.randrange(0, 22))
    files = [{"day": day.isoformat(),
              "rows": [[day.isoformat(), rng.choice(codes), money(rng), rng.choice(words["texts"])]
                       for _ in range(rng.randint(5, 8))]}
             for day in weekdays(start, DAYS)]
    refund, zero = rng.sample(range(DAYS), 2)
    files[refund]["rows"][rng.randrange(len(files[refund]["rows"]))][2] = f"{-rng.randrange(500, 30000) / 100:.2f}"
    files[zero]["rows"][rng.randrange(len(files[zero]["rows"]))][2] = "0.00"
    return {"codes": codes, "unknown": f"{words['prefix']}-{numbers[7]}", "files": files,
            "tests": {"days": [files[0]["day"], files[1]["day"]], "codes": rng.sample(codes, 2),
                      "texts": rng.sample(words["texts"], 2)}}


def special(failure: str, day: str, codes: list, texts, rng: random.Random) -> tuple:
    """A row that stops the importer as made, for one kind of failure: (as written, as meant)."""
    code, text, amount = rng.choice(codes), rng.choice(texts), f"{rng.randrange(100, 99999) / 100:.2f}"
    if failure == "thousands":                  # positive, with one separator: the check tests only what data/ shows
        value = rng.randrange(100000, 9999999) / 100
        return [day, code, f"{value:,.2f}", text], [day, code, f"{value:.2f}", text]
    if failure == "time":
        stamp = f"{day} {rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}"
        return [stamp, code, amount, text], [day, code, amount, text]
    if failure == "padded":
        return [day, code + " " * rng.randint(1, 4), amount, text], [day, code, amount, text]
    return [day, code, amount, ""], [day, code, amount, ""]                       # empty


def draw(seed: int, kind: str, k: int) -> tuple:
    """The k-th task of one kind before its failures: the kind of export (they take turns), then its names."""
    rng = random.Random(f"{SET}:{seed}:{kind}:{k}")
    export = EXPORTS[(k + seed) % len(EXPORTS)]
    task = {"kind": kind, "k": k, "export": export, "name": f"t{rng.getrandbits(48):012x}",
            "template_seed": rng.getrandbits(32), "names": names(export, rng)}
    return task, rng


def fail(task: dict, rng: random.Random) -> list:
    """The failures in data/, drawn after the names. The reported one is in an early file, with clean files before it,
    and in half the tasks comes back in a later file. A `more` task has two more kinds, each in a later file of its
    own. Each failure: its kind, role, file, the row's place among the file's rows, and the row as written and as
    meant; a byte-order mark has no row."""
    words, files = EXPORT_TEXT[task["export"]], task["names"]["files"]
    reported = rng.choice(FAILURES)
    first = rng.randrange(2, 5)
    later = list(range(first + 1, DAYS))
    rng.shuffle(later)
    plan = [(reported, "reported", first)]
    if rng.random() < 0.5:
        plan.append((reported, "again", later.pop()))
    if task["kind"] == "more":
        plan += [(other, "more", later.pop()) for other in rng.sample([f for f in FAILURES if f != reported], 2)]
    out = []
    for failure, role, index in plan:
        found = {"kind": failure, "role": role, "file": index}
        if failure != "bom":
            found["row"] = rng.randrange(len(files[index]["rows"]) + 1)
            found["written"], found["meant"] = special(failure, files[index]["day"], task["names"]["codes"],
                                                       words["texts"], rng)
        out.append(found)
    return out


def hidden(task: dict, rng: random.Random) -> dict:
    """The files the check imports, written into the key and never into the repo, by case, each with what `load` must
    do with it (`must`): import every row right (a file of ordinary rows, one with refunds and an amount of 0, and one
    with rows of each kind that stops a file of the task's data/); stop with BadRowError naming the line of its one row
    that really is wrong (`line`); or, for each kind that the task's data/ doesn't show, either stop or import every row
    right."""
    words, names_ = EXPORT_TEXT[task["export"]], task["names"]
    codes, texts, head = names_["codes"], words["texts"], header(task["export"])
    after = datetime.date.fromisoformat(names_["files"][-1]["day"]) + datetime.timedelta(days=1)
    days = iter(d.isoformat() for d in weekdays(after, 20))

    def ordinary(day: str, count: int) -> list:
        return [[day, rng.choice(codes), f"{rng.randrange(100, 99999) / 100:.2f}", rng.choice(texts)]
                for _ in range(count)]

    found = {}
    day = next(days)
    rows = ordinary(day, 6)
    found["ordinary rows"] = {"file": f"{day}.csv", "text": csv_text(head, rows), "rows": rows, "must": "import",
                              "what": "a file of ordinary rows"}
    for failure in FAILURES:
        day = next(days)
        rows = ordinary(day, 4)
        if failure == "bom":
            text, meant = "\ufeff" + csv_text(head, rows), rows
        else:
            written, meant = list(rows), list(rows)
            for _ in range(3):
                as_written, as_meant = special(failure, day, codes, texts, rng)
                written.insert(rng.randrange(len(written) + 1), as_written)
                meant.append(as_meant)
            text = csv_text(head, written)
        shown_ = failure in kinds_of(task)
        found[("" if shown_ else OTHER) + OUTCOME_CASE[failure]] = {
            "file": f"{day}.csv", "text": text, "rows": meant, "must": "import" if shown_ else "either",
            "what": f"a file with {OUTCOME_CASE[failure]}"}
    code = words["code"]
    taken = {c.split("-")[1] for c in codes + [names_["unknown"]]}        # the visible tests use names_["unknown"]
    unknown = f"{words['prefix']}-{rng.choice([n for n in range(100, 1000) if str(n) not in taken])}"
    for case, what in (("no code", f"a row with no {code}"),
                       ("unknown code", f"a row whose {code} isn't in the list"),
                       ("amount n/a", "a row whose amount is 'n/a'"),
                       ("amount empty", "a row with no amount"),
                       ("date 30 February", "a row dated 2026-02-30"),
                       ("date 30 February with a time", "a row dated 2026-02-30 10:00:00")):
        day = next(days)
        rows = ordinary(day, rng.randint(3, 6))
        wrong = ordinary(day, 1)[0]
        if case == "no code":
            wrong[1] = ""
        elif case == "unknown code":
            wrong[1] = unknown
        elif case == "amount n/a":
            wrong[2] = "n/a"
        elif case == "amount empty":
            wrong[2] = ""
        elif case == "date 30 February":
            wrong[0] = "2026-02-30"
        else:
            wrong[0] = "2026-02-30 10:00:00"
        place = rng.randrange(len(rows) + 1)
        rows.insert(place, wrong)
        found[case] = {"file": f"{day}.csv", "text": csv_text(head, rows), "line": place + 2, "must": "stop",
                       "what": what}
    day = next(days)
    rows = ordinary(day, 2) + [[day, rng.choice(codes), f"{-rng.randrange(500, 30000) / 100:.2f}", rng.choice(texts)]
                               for _ in range(2)] + [[day, rng.choice(codes), "0.00", rng.choice(texts)]]
    rng.shuffle(rows)
    found["refunds and 0"] = {"file": f"{day}.csv", "text": csv_text(head, rows), "rows": rows, "must": "import",
                              "what": "a file with refunds and an amount of 0"}
    return found


def kinds_of(task: dict) -> list:
    """The kinds of failure in the task's data/, in the order of FAILURES."""
    return sorted({f["kind"] for f in task["failures"]}, key=FAILURES.index)


# ----------------------------------------------------------------------------------------------- the repo's files

IMPORTER = '''\
"""Reads @WHAT@.

`load` returns one entry per row; a row that is wrong stops the import with BadRowError."""
from __future__ import annotations

import csv
import json
@IMPORTS@from datetime import datetime
from pathlib import Path

CODES = Path(__file__).with_name("@LIST@")


class BadRowError(Exception):
    """A row that is wrong; the message names its line, counting the header as line 1."""


def load(path) -> list:
    """Every row of the export at `path`, as a dict with `date` (YYYY-MM-DD), `@CODE@`, `amount` and `@TEXT@`."""
    known = set(json.loads(CODES.read_text(encoding="utf-8")))
@READ@@LOOP@

def parse(row: dict, line: int, known: set) -> dict:
    """One row as an entry; BadRowError when it is wrong."""
@DATE@@CODECHECK@@AMOUNT@@TEXTCHECK@    return {"date": date, "@KEYCODE@": @CODE@, "amount": amount, "@KEYTEXT@": @TEXT@}
'''

READ = {None: ('    with open(path, newline="", encoding="utf-8") as f:\n'
               '        rows = list(csv.DictReader(f))\n'),
        "sig": ('    with open(path, newline="", encoding="utf-8-sig") as f:\n'
                '        rows = list(csv.DictReader(f))\n'),
        "fieldnames": ('    with open(path, newline="", encoding="utf-8") as f:\n'
                       '        reader = csv.DictReader(f)\n'
                       '        reader.fieldnames = [name.lstrip("\\ufeff") for name in reader.fieldnames]\n'
                       '        rows = list(reader)\n'),
        "text": ('    text = Path(path).read_text(encoding="utf-8").lstrip("\\ufeff")\n'
                 '    rows = list(csv.DictReader(io.StringIO(text)))\n'),
        "write_back": ('    raw = Path(path).read_bytes()\n'
                       '    if raw.startswith(b"\\xef\\xbb\\xbf"):\n'
                       '        raw = raw[3:]\n'
                       '        Path(path).write_bytes(raw)\n'
                       '    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))\n')}

LOOP = {None: "    return [parse(row, line, known) for line, row in enumerate(rows, 2)]\n",
        "skip": ("    entries = []\n"
                 "    for line, row in enumerate(rows, 2):\n"
                 "        try:\n"
                 "            entries.append(parse(row, line, known))\n"
                 "        except BadRowError:\n"
                 "            continue\n"
                 "    return entries\n"),
        "drop_empty": '    return [parse(row, line, known) for line, row in enumerate(rows, 2) if row["@TEXT@"]]\n'}

NOT_A_DATE = '        raise BadRowError(f"line {line}: date {row[\'date\']!r} is not a date") from None\n'
DATE = {None: ('    date = row["date"]\n'
               '    try:\n'
               '        datetime.strptime(date, "%Y-%m-%d")\n'
               '    except ValueError:\n' + NOT_A_DATE),
        "slice": ('    date = row["date"][:10]\n'
                  '    try:\n'
                  '        datetime.strptime(date, "%Y-%m-%d")\n'
                  '    except ValueError:\n' + NOT_A_DATE),
        "split": ('    date = row["date"].split(" ")[0]\n'
                  '    try:\n'
                  '        datetime.strptime(date, "%Y-%m-%d")\n'
                  '    except ValueError:\n' + NOT_A_DATE),
        "fromiso": ('    try:\n'
                    '        date = datetime.fromisoformat(row["date"]).date().isoformat()\n'
                    '    except ValueError:\n' + NOT_A_DATE),
        "pattern": ('    date = row["date"][:10]\n'
                    '    if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", date):\n'
                    '        raise BadRowError(f"line {line}: date {row[\'date\']!r} is not a date")\n'),
        "pattern_time": ('    date = row["date"]\n'
                         '    if " " in date:\n'
                         '        if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}", date):\n'
                         '            raise BadRowError(f"line {line}: date {row[\'date\']!r} is not a date")\n'
                         '        date = date[:10]\n'
                         '    else:\n'
                         '        try:\n'
                         '            datetime.strptime(date, "%Y-%m-%d")\n'
                         '        except ValueError:\n'
                         '    ' + NOT_A_DATE)}

NOT_A_NUMBER = '        raise BadRowError(f"line {line}: amount {row[\'amount\']!r} is not a number") from None\n'
AMOUNT = {None: ('    try:\n'
                 '        amount = float(row["amount"])\n'
                 '    except ValueError:\n' + NOT_A_NUMBER),
          "replace": ('    try:\n'
                      '        amount = float(row["amount"].replace(",", ""))\n'
                      '    except ValueError:\n' + NOT_A_NUMBER),
          "regex": ('    text = row["amount"]\n'
                    '    if re.fullmatch(r"-?\\d{1,3}(,\\d{3})+(\\.\\d+)?", text):\n'
                    '        text = text.replace(",", "")\n'
                    '    try:\n'
                    '        amount = float(text)\n'
                    '    except ValueError:\n' + NOT_A_NUMBER),
          "decimal": ('    try:\n'
                      '        amount = float(Decimal(row["amount"].replace(",", "")))\n'
                      '    except InvalidOperation:\n' + NOT_A_NUMBER),
          "zero": ('    try:\n'
                   '        amount = float(row["amount"].replace(",", ""))\n'
                   '    except ValueError:\n'
                   '        amount = 0.0\n'),
          "empty_zero": ('    try:\n'
                         '        amount = float(row["amount"].replace(",", "") or 0)\n'
                         '    except ValueError:\n' + NOT_A_NUMBER),
          "decimal_raw": ('    try:\n'
                          '        amount = Decimal(row["amount"].replace(",", ""))\n'
                          '    except InvalidOperation:\n' + NOT_A_NUMBER),
          "string_amount": ('    amount = row["amount"].replace(",", "")\n'
                            '    try:\n'
                            '        float(amount)\n'
                            '    except ValueError:\n' + NOT_A_NUMBER)}
NO_REFUND = ('    if amount < 0:\n'
             '        raise BadRowError(f"line {line}: amount {row[\'amount\']!r} is below 0")\n')


def code_check(code: str, style) -> str:
    """The lines that read and check a row's code: as made, or fixed for padding in a style; "lookup", which looks the
    code up without its padding but keeps the padding in the entry, over-reaches."""
    read = {None: f'row["{code}"]', "strip": f'row["{code}"].strip()', "rstrip": f'row["{code}"].rstrip()',
            "regex": f're.sub(r"\\s+$", "", row["{code}"])', "lookup": f'row["{code}"]'}[style]
    known = f"{code}.strip()" if style == "lookup" else code
    return (f"    {code} = {read}\n"
            f"    if not {code}:\n"
            f'        raise BadRowError(f"line {{line}}: no {code}")\n'
            f"    if {known} not in known:\n"
            f'        raise BadRowError(f"line {{line}}: unknown {code} {{{code}!r}}")\n')


def text_check(text: str, style) -> str:
    """The lines that read a row's text: as made, which refuses an empty one, or fixed in a style."""
    if style == "drop":
        return f'    {text} = row["{text}"]\n'
    if style == "none":
        return f'    {text} = row["{text}"] or None\n'
    return (f'    {text} = row["{text}"]\n'
            f"    if not {text}:\n"
            f'        raise BadRowError(f"line {{line}}: {text} is empty")\n')


def importer_source(task: dict, build=None) -> str:
    """<package>/importer.py: as made, or with `build`: the kinds of failure it fixes, each in a style ({kind: style}
    under "fix"), and any of the flags that over-reach, each taking the place of a fix: skip (rows that stop are
    skipped), zero and empty_zero (a non-number, or an empty amount, reads as 0), decimal_raw (amounts are Decimals,
    which the command can't add), string_amount (amounts are text), pattern_date and pattern_time (a date, or a date
    with a time, is checked by its pattern alone), rename (an entry's code and text fields are renamed), no_refund (a
    negative amount stops the import), write_back (a byte-order mark is taken off the file being read, on disk), lookup
    (a padded code keeps its padding), drop_empty (rows with an empty text are dropped)."""
    words = EXPORT_TEXT[task["export"]]
    b = {"fix": {}, **(build or {})}
    fix = b["fix"]
    amount = next((flag for flag in ("zero", "empty_zero", "decimal_raw", "string_amount") if b.get(flag)),
                  fix.get("thousands"))
    date = "pattern" if b.get("pattern_date") else "pattern_time" if b.get("pattern_time") else fix.get("time")
    read = "write_back" if b.get("write_back") else fix.get("bom")
    loop = "skip" if b.get("skip") else "drop_empty" if b.get("drop_empty") else None
    padded = "lookup" if b.get("lookup") else fix.get("padded")
    imports = "".join(line for line, needed in (
        ("import io\n", read in ("text", "write_back")),
        ("import re\n", amount == "regex" or date in ("pattern", "pattern_time") or padded == "regex"),
        ("from decimal import Decimal, InvalidOperation\n", amount in ("decimal", "decimal_raw"))) if needed)
    return (IMPORTER.replace("@IMPORTS@", imports).replace("@READ@", READ[read])
            .replace("@LOOP@", LOOP[loop]).replace("@DATE@", DATE[date])
            .replace("@CODECHECK@", code_check(words["code"], padded))
            .replace("@AMOUNT@", AMOUNT[amount] + (NO_REFUND if b.get("no_refund") else ""))
            .replace("@TEXTCHECK@", text_check(words["text"], "drop" if b.get("drop_empty") else fix.get("empty")))
            .replace("@KEYCODE@", "code" if b.get("rename") else words["code"])
            .replace("@KEYTEXT@", "text" if b.get("rename") else words["text"])
            .replace("@WHAT@", words["what"]).replace("@LIST@", words["list"])
            .replace("@CODE@", words["code"]).replace("@TEXT@", words["text"]))


MAIN = '''\
"""python3 -m @PACKAGE@ import FILE: import one export, and print how many rows it had and the total for each @CODE@."""
import sys
from collections import defaultdict

from .importer import @MAINIMPORT@


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] != "import":
        print("usage: python3 -m @PACKAGE@ import FILE", file=sys.stderr)
        return 2
@LOAD@    totals = defaultdict(float)
    for entry in entries:
        totals[entry["@CODE@"]] += entry["amount"]
    print(f"Imported {len(entries)} rows.")
    for code in sorted(totals):
        print(f"{code}: {totals[code]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
# How the command loads a file: as made, or, over-reaching (lenient_main), carrying on past a wrong row.
MAIN_LOAD = {False: ("load", "    entries = load(args[1])\n"),
             True: ("BadRowError, load", ('    try:\n'
                                          '        entries = load(args[1])\n'
                                          '    except BadRowError as error:\n'
                                          '        print(f"skipped the file: {error}", file=sys.stderr)\n'
                                          '        return 0\n'))}

TESTS = '''\
"""Tests for the importer, with temporary files."""
import os
import tempfile
import unittest

from @PACKAGE@.importer import BadRowError, load

HEADER = "date,@CODE@,amount,@TEXT@\\n"


class ImporterTest(unittest.TestCase):
    def load_rows(self, *lines):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "export.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(HEADER + "".join(line + "\\n" for line in lines))
            return load(path)

    def assertStops(self, line, *lines):
        with self.assertRaises(BadRowError) as raised:
            self.load_rows(*lines)
        self.assertRegex(str(raised.exception), r"(?<![0-9])%d(?![0-9])" % line)

    def test_ordinary_rows(self):
        got = self.load_rows("@D1@,@C1@,42.50,@T1@", "@D2@,@C2@,1250.00,@T2@")
        self.assertEqual(len(got), 2)
        self.assertEqual(str(got[0]["date"])[:10], "@D1@")
        self.assertEqual(got[0]["@CODE@"], "@C1@")
        self.assertAlmostEqual(float(got[0]["amount"]), 42.5)
        self.assertEqual(got[0]["@TEXT@"], "@T1@")
        self.assertEqual(str(got[1]["date"])[:10], "@D2@")
        self.assertAlmostEqual(float(got[1]["amount"]), 1250.0)

    def test_a_refund_and_an_amount_of_0(self):
        got = self.load_rows("@D1@,@C1@,-12.40,@T1@", "@D1@,@C2@,0.00,@T2@")
        self.assertAlmostEqual(float(got[0]["amount"]), -12.4)
        self.assertAlmostEqual(float(got[1]["amount"]), 0.0)

    def test_a_row_with_no_@CODE@_stops_the_import(self):
        self.assertStops(3, "@D1@,@C1@,10.00,@T1@", "@D1@,,10.00,@T1@")

    def test_an_unknown_@CODE@_stops_the_import(self):
        self.assertStops(2, "@D1@,@UNKNOWN@,10.00,@T1@")

    def test_an_amount_that_isnt_a_number_stops_the_import(self):
        self.assertStops(2, "@D1@,@C1@,ten,@T1@")

    def test_a_date_that_isnt_a_date_stops_the_import(self):
        self.assertStops(2, "2026-13-01,@C1@,10.00,@T1@")


if __name__ == "__main__":
    unittest.main()
'''
TESTS_RUN = 6

README = '''\
# @TITLE@ import

Reads @WHAT@, one CSV file a day.

`load(path)` in `@PACKAGE@/importer.py` returns one entry per row: a dict with `date` (YYYY-MM-DD), `@CODE@`,
`amount` (a number) and `@TEXT@`.

- `@CODE@` must be one of those in `@PACKAGE@/@LIST@`.
- A negative `amount` is a refund, and an amount of 0 is allowed.
- `@TEXT@` may be empty.

A row that is wrong (one with no @CODE@, a @CODE@ that isn't in the list, an amount that isn't a number or a date that
isn't a date) stops the import with `BadRowError`, whose message names the row's line; the header is line 1.

    python3 -m @PACKAGE@ import data/@FIRST@.csv

imports one export and prints how many rows it had and the total for each @CODE@. The exports received so far are in
`data/`.

## Tests

Standard library only; runs on Python 3.9 or later.

    python3 -m unittest
'''


def header(export: str) -> list:
    words = EXPORT_TEXT[export]
    return ["date", words["code"], "amount", words["text"]]


def csv_text(head: list, rows: list) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(head)
    writer.writerows(rows)
    return out.getvalue()


def export_text(task: dict, index: int) -> str:
    """One export in data/, as its file holds it: the header and the rows, with each planned failure in its place."""
    rows = [list(row) for row in task["names"]["files"][index]["rows"]]
    mark = ""
    for found in sorted((f for f in task["failures"] if f["file"] == index), key=lambda f: f.get("row", 0)):
        if found["kind"] == "bom":
            mark = "\ufeff"
        else:
            rows.insert(found["row"], found["written"])
    return mark + csv_text(header(task["export"]), rows)


def meant_rows(task: dict, index: int) -> list:
    """The rows of one export in data/ as they are meant: what a right import of the file gives."""
    rows = [list(row) for row in task["names"]["files"][index]["rows"]]
    return rows + [f["meant"] for f in task["failures"] if f["file"] == index and f["kind"] != "bom"]


def fill(text: str, **values) -> str:
    for name, value in values.items():
        text = text.replace(f"@{name}@", value)
    return text


def files(task: dict, build=None) -> dict:
    """The repo's files, {path: text}: as made, or with `build` in place of the importer (`importer_source`); three
    more flags over-reach outside it: pad_list adds the padded codes seen in data/ to the code list, edit_data writes
    every file in data/ as it is meant, and lenient_main makes the command carry on past a wrong row."""
    words, names_, package = EXPORT_TEXT[task["export"]], task["names"], task["export"]
    t = names_["tests"]
    values = dict(PACKAGE=package, CODE=words["code"], TEXT=words["text"], LIST=words["list"], WHAT=words["what"],
                  TITLE=words["title"], FIRST=names_["files"][0]["day"], UNKNOWN=names_["unknown"], D1=t["days"][0],
                  D2=t["days"][1], C1=t["codes"][0], C2=t["codes"][1], T1=t["texts"][0], T2=t["texts"][1])
    codes = list(names_["codes"])
    if build and build.get("pad_list"):
        codes += sorted({f["written"][1] for f in task["failures"] if f["kind"] == "padded"})
    names, load_lines = MAIN_LOAD[bool(build and build.get("lenient_main"))]
    main = MAIN.replace("@MAINIMPORT@", names).replace("@LOAD@", load_lines)
    found = {"README.md": fill(README, **values), ".gitignore": "__pycache__/\n", f"{package}/__init__.py": "",
             f"{package}/__main__.py": fill(main, **values), f"{package}/importer.py": importer_source(task, build),
             f"{package}/{words['list']}": json.dumps(codes, indent=1) + "\n", "tests/__init__.py": "",
             "tests/test_importer.py": fill(TESTS, **values)}
    for index, day in enumerate(names_["files"]):
        found[f"data/{day['day']}.csv"] = (csv_text(header(package), meant_rows(task, index))
                                           if build and build.get("edit_data") else export_text(task, index))
    return found


def write(root: Path, found: dict) -> Path:
    for path, text in found.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_bytes(text.encode("utf-8"))
    return root


# --------------------------------------------------------------------------------- the request and what it states

def stops_with(task: dict, found: dict) -> str:
    """The last line the importer as made prints for a file that one failure stops."""
    words = EXPORT_TEXT[task["export"]]
    if found["kind"] == "bom":
        return "KeyError: 'date'"
    written, line = found["written"], found["row"] + 2
    said = {"thousands": f"amount {written[2]!r} is not a number", "time": f"date {written[0]!r} is not a date",
            "padded": f"unknown {words['code']} {written[1]!r}", "empty": f"{words['text']} is empty"}[found["kind"]]
    return f"{task['export']}.importer.BadRowError: line {line}: {said}"


def reported(task: dict) -> dict:
    return next(f for f in task["failures"] if f["role"] == "reported")


def prompt(task: dict) -> str:
    """The request: the reported file's command, the last line it prints, and "Please fix it."."""
    found = reported(task)
    day = task["names"]["files"][found["file"]]["day"]
    return (f"Running `python3 -m {task['export']} import data/{day}.csv` stops with `{stops_with(task, found)}`. "
            "Please fix it.")


def goal(task: dict) -> str:
    words = EXPORT_TEXT[task["export"]]
    return (f"Make the import work on every file {words['who']} sends, like the ones in data/, while a row that really "
            "is wrong still stops it with BadRowError naming its line.")


def planned_stop(task: dict, index: int):
    """The last line the importer as made should print for one file of data/, or None when it imports."""
    found = [f for f in task["failures"] if f["file"] == index]
    return stops_with(task, found[0]) if found else None


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def key_of(task: dict) -> dict:
    """What the check needs, and what a later check of each brief reads: the fields, the cases and their files, the
    repo's tests as committed, the hashes of data/ and the code list, each fact's role, and the failures in data/."""
    words, made = EXPORT_TEXT[task["export"]], files(task)
    roles = {text: role for role, text in fact_texts(task["export"]).items()}
    keep = [p for p in made if p.startswith("data/")] + [f"{task['export']}/{words['list']}"]
    return {"set": SET, "export": task["export"], "package": task["export"],
            "fields": {"date": "date", "code": words["code"], "amount": "amount", "text": words["text"]},
            "failures": kinds_of(task), "cases": ["ordinary rows"] + [OUTCOME_CASE[f] for f in kinds_of(task)]
            + list(SCOPE_CASES) + [OTHER + OUTCOME_CASE[f] for f in FAILURES if f not in kinds_of(task)],
            "hidden": task["hidden"],
            "tests": {"tests/__init__.py": "", "tests/test_importer.py": made["tests/test_importer.py"]},
            "unchanged": {p: sha256(made[p]) for p in keep},
            "facts": [{"text": text, "role": roles[text]} for text in facts(task)],
            "data": [{"file": f"data/{task['names']['files'][f['file']]['day']}.csv", "kind": f["kind"],
                      "role": f["role"], "line": f.get("row", -2) + 2 if f["kind"] != "bom" else None,
                      "stops_with": stops_with(task, f)} for f in task["failures"]],
            "request": {"file": f"data/{task['names']['files'][reported(task)['file']]['day']}.csv",
                        "stops_with": stops_with(task, reported(task))}}


# ----------------------------------------------------------------------------------------------- the hidden cases

def load_module(root: Path, module: str):
    """`module` from the code under root, imported afresh: nothing of an earlier import is kept."""
    forget(module.split(".")[0])
    importlib.invalidate_caches()
    sys.path.insert(0, str(root))
    return importlib.import_module(module)


def forget(*packages: str) -> None:
    for name in [n for n in sys.modules if any(n == p or n.startswith(p + ".") for p in packages)]:
        del sys.modules[name]


def unload(root: Path, *packages: str) -> None:
    forget(*packages)
    with contextlib.suppress(ValueError):
        sys.path.remove(str(root))


def describe(error: BaseException, root: Path | None = None) -> str:
    if isinstance(error, SyntaxError):
        where = error.filename or "?"
        if root and where.startswith(str(root)):
            where = where[len(str(root)) + 1:]
        return f"SyntaxError in {where}, line {error.lineno}: {error.msg}"
    return f"{type(error).__name__}: {error}"


def field(thing, name):
    """An entry's field, from a dict or an object."""
    return thing.get(name) if isinstance(thing, dict) else getattr(thing, name, None)


def values(entry, fields: dict) -> tuple:
    """An entry's date, code, amount and text as the check compares them: the date's first ten characters, the code as
    it is, the amount as a Decimal when it is a number (an int, float or Decimal; the README says a number, so text is
    None, as is a bool), the text trimmed; None for a field the entry doesn't have."""
    date, code, amount, text = (field(entry, fields[name]) for name in ("date", "code", "amount", "text"))
    number = None
    if isinstance(amount, (int, float, Decimal)) and not isinstance(amount, bool):
        with contextlib.suppress(InvalidOperation, ValueError):
            number = Decimal(str(amount))
            if not number.is_finite():
                number = None
    return (str(date)[:10] if date is not None else None, str(code) if code is not None else None, number,
            str(text).strip() if text is not None else None)


def matches(got: tuple, want: list) -> bool:
    date, code, amount, text = got
    return (date == want[0] and code == want[1] and amount is not None
            and abs(amount - Decimal(want[2])) <= Decimal("0.005") and (want[3] == "" or text == want[3]))


def shown(got: tuple, fields: dict) -> str:
    date, code, amount, text = got
    return f"date {date}, {fields['code']} {code!r}, amount {amount}, {fields['text']} {text!r}"


def same_rows(entries: list, want: list, fields: dict):
    """None when `entries` hold exactly the rows `want` lists, in any order; else what differs, in plain words."""
    if len(entries) != len(want):
        return f"load gave {len(entries)} rows; the file has {len(want)}"
    left = list(want)
    for entry in entries:
        got = values(entry, fields)
        found = next((w for w in left if matches(got, w)), None)
        if found is None:
            return f"load gave a row that doesn't match the file: {shown(got, fields)}"
        left.remove(found)
    return None


def says_line(text: str, line: int) -> bool:
    """Whether a message names this line as a whole number. Paths are left out first: the folders a case reads from
    have random names, which may hold the number."""
    return re.search(rf"(?<![0-9]){line}(?![0-9])", re.sub(r"\S*/\S*", " ", text)) is not None


def names_line(error: BaseException, line: int) -> bool:
    """Whether an error names this line: as its `line`, or as a whole number in its message."""
    return getattr(error, "line", None) == line or says_line(str(error), line)


def run_case(key: dict, name: str, root: Path) -> tuple:
    """One hidden case, on the code under root: (passed, what happened in plain words)."""
    try:
        if name == "data unchanged":
            return unchanged(key, root)
        if name == "the repo's tests":
            return repo_tests(key, root)
        if name == "the command":
            return command_case(key, root)
        return import_case(key, name, root)
    except (Exception, SystemExit) as error:                     # the code under test can raise anything
        return False, f"it raised {describe(error, root)}"


def import_case(key: dict, name: str, root: Path) -> tuple:
    """A case that imports one of the hidden files with `load`, which must leave the file as it was. As the case
    says (`must`): every row must come out right (import); its wrong row must stop the import with BadRowError naming
    the row's line (stop); or, for a kind of failure that the task's data/ doesn't show, the file may stop the import,
    with any error, but must not import wrong (either)."""
    case, module = key["hidden"][name], key["package"] + ".importer"
    what, must = case["what"], case["must"]
    with tempfile.TemporaryDirectory(prefix="import-case-") as place:
        path, written = Path(place, case["file"]), case["text"].encode("utf-8")
        path.write_bytes(written)
        try:
            loaded = load_module(root, module)
        except (Exception, SystemExit) as error:
            unload(root, key["package"])
            return False, f"the code doesn't import: {describe(error, root)}"
        bad, entries, error = getattr(loaded, "BadRowError", None), None, None
        try:
            entries = list(loaded.load(str(path)))
        except (Exception, SystemExit) as raised:
            error = raised
        finally:
            unload(root, key["package"])
        if path.is_symlink() or not path.is_file() or path.read_bytes() != written:
            return False, f"{what}: load changed the file it read"
    if must == "stop":
        if error is None:
            return False, f"{what}, at line {case['line']}, imported instead of stopping the import"
        if not (isinstance(bad, type) and isinstance(error, bad)):
            return False, f"{what}, at line {case['line']}, raised {describe(error)}, not BadRowError"
        if not names_line(error, case["line"]):
            return False, f"{what}, at line {case['line']}, raised BadRowError without naming the line: {error}"
        return True, f"{what}, at line {case['line']}, stops the import with BadRowError naming the line"
    if error is not None:
        if must == "either":
            return True, f"{what}, a kind data/ doesn't show, stops the import: {describe(error)}"
        return False, f"{what} raised {describe(error)}"
    problem = same_rows(entries, case["rows"], key["fields"])
    if problem:
        return False, f"{what}: {problem}" + (" (a kind data/ doesn't show may stop the import, but not import "
                                              "wrong)" if must == "either" else "")
    return True, f"{what} imports, all {len(case['rows'])} rows with the right values"


def command_case(key: dict, root: Path) -> tuple:
    """The requester's command, `python3 -m <package> import FILE`, run in root on new files, each of which it must
    leave as it was: it must import a file of ordinary rows and one with refunds and an amount of 0, and stop on a file
    with a row with no code, naming the row's line in the last line it prints. A fix that breaks the command, or makes
    it carry on past a wrong row, fails here even when `load` passes."""
    package = key["package"]
    with tempfile.TemporaryDirectory(prefix="import-command-") as place:
        for name, works in (("ordinary rows", True), ("refunds and 0", True), ("no code", False)):
            case = key["hidden"][name]
            path, written = Path(place, case["file"]), case["text"].encode("utf-8")
            path.write_bytes(written)
            env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": place, "TMPDIR": place}
            try:
                done = subprocess.run([sys.executable, "-B", "-m", package, "import", str(path)], cwd=root, env=env,
                                      capture_output=True, text=True, timeout=CASE_SECONDS, stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                return False, f"`python3 -m {package} import` took more than {CASE_SECONDS} seconds on {case['what']}"
            said = [line for line in (done.stderr.strip() or done.stdout).splitlines() if line.strip()]
            last = said[-1] if said else ""
            if path.is_symlink() or not path.is_file() or path.read_bytes() != written:
                return False, f"`python3 -m {package} import` changed the file it imported, {case['what']}"
            if works and done.returncode != 0:
                return False, f"`python3 -m {package} import` failed on {case['what']}: {last}"
            if not works and done.returncode == 0:
                return False, (f"`python3 -m {package} import` carried on past {case['what']} at line {case['line']}"
                               f" and exited 0" + (f": {last}" if last else ""))
            if not works and not says_line(last, case["line"]):
                return False, (f"`python3 -m {package} import` stopped on {case['what']} without naming line "
                               f"{case['line']}: {last}")
    return True, (f"`python3 -m {package} import` imports a file of ordinary rows and one with refunds and an amount of "
                  "0, and stops at a wrong row's line")


def unchanged(key: dict, root: Path) -> tuple:
    """The files in data/ and the code list keep their bytes; new files are allowed."""
    changed = [p for p, digest in key["unchanged"].items()
               if (root / p).is_symlink() or not (root / p).is_file()
               or hashlib.sha256((root / p).read_bytes()).hexdigest() != digest]
    if changed:
        return False, (f"{len(changed)} file{'s' if len(changed) > 1 else ''} the request didn't ask to change "
                       f"changed or went: {', '.join(changed[:4])}{' ...' if len(changed) > 4 else ''}")
    return True, f"the {len(key['unchanged']) - 1} files in data/ and the {key['fields']['code']} list keep their bytes"


def repo_tests(key: dict, root: Path) -> tuple:
    """The repo's own tests, as committed, run on the code under root (a copy, so the tests can be written back)."""
    for path, text in key["tests"].items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    forget(key["package"], "tests")
    importlib.invalidate_caches()
    sys.path.insert(0, str(root))
    try:
        suite = unittest.TestLoader().loadTestsFromName("tests.test_importer")
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        unload(root, key["package"], "tests")
    if result.wasSuccessful() and result.testsRun == TESTS_RUN:
        return True, f"the repo's {TESTS_RUN} tests, as committed, pass"
    failed = [test.id().rsplit(".", 1)[-1] for test, _ in result.failures + result.errors]
    return False, (f"{len(failed)} of the repo's {result.testsRun} tests, as committed, fail: {', '.join(failed)}"
                   if failed else f"the repo's tests ran {result.testsRun} of {TESTS_RUN}")


def cases(key: dict) -> list:
    return list(key["cases"])


def group(name: str) -> str:
    """outcome for a case of what the requester is after (ordinary rows, and each kind of failure in the task's data/);
    scope for a case of over-reach."""
    return "outcome" if name == "ordinary rows" or name in OUTCOME_CASE.values() else "scope"


def failing(key: dict, root: Path) -> list:
    """The cases the code under root fails, run here rather than in child processes, as `make` checks a task."""
    return [name for name in cases(key) if not run_case(key, name, root)[0]]


def passes(key: dict, root: Path) -> bool:
    return all(run_case(key, name, root)[0] for name in cases(key))


def check(key_path: Path, root: Path) -> int:
    """The hidden check: every case in a child process of its own; exit 0 only when every case passes."""
    key = json.loads(Path(key_path).read_text())
    print(f"Python {platform.python_version()} ({sys.executable})")
    failed = 0
    for name in cases(key):
        passed, message = child(key_path, name, root)
        failed += not passed
        print(f"{'PASS' if passed else 'FAIL'}  {group(name)}: {name}: {message}")
    total = len(cases(key))
    print(f"{failed} of {total} cases failed." if failed else f"All {total} cases passed.")
    return 1 if failed else 0


def child(key_path: Path, name: str, root: Path) -> tuple:
    """Run one case in a child process, on a fresh copy of the code (links copied as links), with an empty home and
    temporary folder, nothing else in its environment but PATH, and a time limit."""
    with tempfile.TemporaryDirectory(prefix="import-case-") as place:
        place = Path(place)
        copy, home, temp, out = place / "code", place / "home", place / "tmp", place / "result.json"
        try:
            shutil.copytree(root, copy, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        except (OSError, shutil.Error) as error:
            return False, f"the code couldn't be copied to run: {describe(error)}"
        home.mkdir()
        temp.mkdir()
        env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home), "TMPDIR": str(temp)}
        argv = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "case", "--key", str(Path(key_path).resolve()),
                "--case", name, "--root", str(copy), "--out", str(out)]
        try:
            done = subprocess.run(argv, cwd=copy, env=env, capture_output=True, text=True, timeout=CASE_SECONDS,
                                  stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return False, f"it took more than {CASE_SECONDS} seconds"
        if not out.is_file():
            said = (done.stderr.strip() or done.stdout.strip()).splitlines()
            return False, "it stopped without a result" + (f": {said[-1]}" if said else "")
        result = json.loads(out.read_text())
        return bool(result["passed"]), str(result["message"])


# -------------------------------------------------------------------------------------------------- making a set

def order(more: int, only: int) -> list:
    """The tasks in the order they run, (kind, k) for the k-th of its kind: the two kinds spread evenly."""
    totals, done, out = {"more": more, "only": only}, {"more": 0, "only": 0}, []
    for _ in range(more + only):
        kind = min((k for k in KINDS if done[k] < totals[k]), key=lambda k: ((done[k] + 0.5) / totals[k], k))
        out.append((kind, done[kind]))
        done[kind] += 1
    return out


def fix(kinds, n: int = 0) -> dict:
    """A build that fixes these kinds of failure, each in its n-th style."""
    return {"fix": {k: STYLES[k][n % len(STYLES[k])] for k in kinds}}


def harmful(task: dict, harm: str) -> dict:
    """A build that fixes every kind of failure in data/ and over-reaches in one way. Adding padded codes to the code
    list stands in for fixing padded codes, so it needs a task with padded codes."""
    every = kinds_of(task)
    if harm == "pad_list":
        return {**fix([k for k in every if k != "padded"]), "pad_list": True}
    return {**fix(every), harm: True}


def run_import(root: Path, day: str, package: str, python: str) -> tuple:
    """`python3 -m <package> import data/<day>.csv` in root, as the requester runs it: (exit code, last line on
    stderr)."""
    with tempfile.TemporaryDirectory(prefix="import-run-") as home:
        env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": home, "TMPDIR": home}
        done = subprocess.run([python, "-B", "-m", package, "import", f"data/{day}.csv"], cwd=root, env=env,
                              capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    lines = [line for line in done.stderr.splitlines() if line.strip()]
    return done.returncode, (lines[-1] if lines else "")


def problems(task: dict, python: str | None = None) -> list:
    """What would make a task unfair: a file in data/ that doesn't stop as planned, or the reported one with another
    line than the request's; the repo as made failing anything but the outcome cases of the task's kinds; a reference
    fix, or a fix of all five kinds, failing a case; fixing only the reported kind failing an `only` task, or failing
    a `more` one on anything but the outcome cases of its two other kinds; in a `more` task, a fix that leaves one
    kind unfixed passing; a fix that over-reaches passing; the repo's tests failing as made. Empty when there is
    nothing."""
    python = python or sys.executable
    key, found, every = key_of(task), [], kinds_of(task)
    with tempfile.TemporaryDirectory(prefix="import-verify-") as place:
        place = Path(place)
        made = write(place / "made", files(task))
        for index, day in enumerate(task["names"]["files"]):
            want, got = planned_stop(task, index), run_import(made, day["day"], task["export"], python)
            if (want is None and got[0] != 0) or (want is not None and got != (1, want)):
                found.append(f"data/{day['day']}.csv gives {got}; planned {want or 'a clean import'}")
        if not repo_tests(key, place / "made")[0]:
            found.append("the repo's tests fail as made")
        if failing(key, made) != [OUTCOME_CASE[k] for k in every]:
            found.append(f"the repo as made fails {failing(key, made)}, not the outcome cases of its kinds")
        for n in range(3):
            reference = write(place / f"reference-{n}", files(task, fix(every, n)))
            failed = [(c, m) for c, (ok, m) in ((c, run_case(key, c, reference)) for c in cases(key)) if not ok]
            if failed:
                found.append(f"reference fix {n} fails: {failed}")
            for index, day in enumerate(task["names"]["files"]):
                loaded = load_module(reference, f"{task['export']}.importer")
                try:
                    problem = same_rows(list(loaded.load(str(reference / f"data/{day['day']}.csv"))),
                                        meant_rows(task, index), key["fields"])
                except Exception as error:
                    problem = describe(error)
                finally:
                    unload(reference, task["export"])
                if problem:
                    found.append(f"reference fix {n} on data/{day['day']}.csv: {problem}")
        if not passes(key, write(place / "all", files(task, fix(FAILURES)))):
            found.append("a fix of all five kinds fails")
        first = reported(task)["kind"]
        for n in range(3):
            literal = write(place / f"literal-{n}", files(task, fix([first], n)))
            want = [OUTCOME_CASE[k] for k in every if k != first]
            if failing(key, literal) != want:
                found.append(f"fixing only the reported kind, style {n}, fails {failing(key, literal)}, not {want}")
        if task["kind"] == "more":
            for left in every:
                if passes(key, write(place / f"without-{left}", files(task, fix([k for k in every if k != left])))):
                    found.append(f"a fix that leaves {left} unfixed passes")
        for harm in HARMFUL:
            if harm == "pad_list" and "padded" not in every:
                continue
            if passes(key, write(place / f"harm-{harm}", files(task, harmful(task, harm)))):
                found.append(f"a fix that over-reaches ({harm}) passes")
    return found


def plan(seed: int, kind: str, k: int, verify: bool = True, python: str | None = None) -> dict:
    """Everything about the k-th task of one kind, drawn from the seed: the names first, then the failures and the
    hidden files, drawn again (never the names) until `problems` finds nothing."""
    task, rng = draw(seed, kind, k)
    for attempt in range(1, 101):
        task["failures"] = fail(task, rng)
        task["hidden"] = hidden(task, rng)
        task["attempts"] = attempt
        if not verify or not problems(task, python):
            return task
    raise RuntimeError(f"no failures for task {task['name']} were fair in 100 draws")


def git(repo: Path, *args: str) -> str:
    """git with a fixed author, dates and settings, and none of yours, so a seed always gives the same commit."""
    stamp, who = "2026-10-01T00:00:00Z", ("briefbench", "briefbench@example.invalid")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp, "GIT_AUTHOR_NAME": who[0],
                "GIT_AUTHOR_EMAIL": who[1], "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1],
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}",
                           "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false", *args], cwd=repo, env=env,
                          check=True, capture_output=True, text=True).stdout.strip()


def worker_python(here: Path) -> str:
    """The python3 a sandboxed worker finds: the first on PATH outside this checkout, where the bench's virtualenv
    lives, and outside any active virtualenv (the bench takes both off the worker's PATH)."""
    skip = [here] + ([Path(os.environ["VIRTUAL_ENV"]).resolve()] if os.environ.get("VIRTUAL_ENV") else [])
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not folder:
            continue
        place = Path(folder).resolve()
        if any(place == s or s in place.parents for s in skip):
            continue
        candidate = Path(folder) / "python3"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise SystemExit("No python3 on PATH outside the bench's virtualenv; name one with --python.")


def make(seed: int, more: int, only: int, out: Path, keys: Path, python: str | None = None) -> list:
    """Write `more` + `only` task repos under `out` and their task files, keys and checker under `keys`, with
    keys/tasks.txt listing the task files in order (`order`). Both folders must be new or empty."""
    out, keys = out.resolve(), keys.resolve()
    if out == keys or out in keys.parents or keys in out.parents:
        raise SystemExit("--out and --keys must be separate folders, neither inside the other.")
    if more < 0 or only < 0 or more + only == 0:
        raise SystemExit("--more and --only are how many tasks of each kind to write: at least one in all.")
    python = python or worker_python(Path(__file__).resolve().parents[2])
    try:
        version = subprocess.run([python, "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                                 capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise SystemExit(f"{python} doesn't run; name a working python3 with --python.") from None
    if tuple(int(x) for x in version.split(".")[:2]) < (3, 9):
        raise SystemExit(f"{python} is Python {version}; the tasks need 3.9 or later.")
    for folder in (out, keys):
        if folder.exists() and any(folder.iterdir()):
            raise SystemExit(f"{folder} isn't empty; make writes a fresh set.")
        folder.mkdir(parents=True, exist_ok=True)
    script = keys / "failing_import.py"          # the checks run this copy, so they outlive the checkout that made it
    shutil.copyfile(Path(__file__).resolve(), script)
    generator = hashlib.sha256(script.read_bytes()).hexdigest()
    written = []
    for kind, k in order(more, only):
        task = plan(seed, kind, k, python=python)
        repo = write(out / task["name"], files(task))
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "Initial version")
        folder = keys / task["name"]
        folder.mkdir()
        (folder / "key.json").write_text(json.dumps(key_of(task), indent=1) + "\n")
        command = shlex.join([python, "-I", str(script), "check", "--key", str(folder / "key.json")])
        (folder / "task.json").write_text(json.dumps({
            "format": 1, "id": task["name"], "set": SET, "stratum": kind, "repo": str(repo),
            "commit": git(repo, "rev-parse", "HEAD"), "type": "code", "prompt": prompt(task), "goal": goal(task),
            "check": command, "setup": "", "protected": [], "facts": facts(task), "generator_sha256": generator,
            "checker_sha256": generator}, indent=1) + "\n")
        written.append(folder / "task.json")
    (keys / "tasks.txt").write_text("".join(f"{f.relative_to(keys)}\n" for f in written))
    (keys / "set.json").write_text(json.dumps({"set": SET, "seed": seed, "more": more, "only": only, "repos": str(out),
                                               "generator_sha256": generator, "python": python,
                                               "python_version": version}, indent=1) + "\n")
    return written


def explain(seed: int, more: int, only: int) -> list:
    """Each task's id, kind, export and failures, regenerated from the seed, in the order `make` writes them. Print it
    only after the experiment: it holds the answers."""
    found = []
    for kind, k in order(more, only):
        task = plan(seed, kind, k)
        key = key_of(task)
        found.append({"id": task["name"], "kind": kind, "stratum": kind, "export": task["export"],
                      "request": key["request"], "data": key["data"], "attempts": task["attempts"]})
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    m = commands.add_parser("make", help="write a set of tasks")
    e = commands.add_parser("explain", help="print each task's failures, regenerated from the seed")
    for p in (m, e):
        p.add_argument("--seed", type=int, required=True)
        p.add_argument("--more", type=int, required=True, help="tasks whose data/ holds two more kinds that stop")
        p.add_argument("--only", type=int, required=True, help="tasks whose reported kind is the only one")
    m.add_argument("--out", type=Path, required=True, help="a new folder for the task repos")
    m.add_argument("--keys", type=Path, required=True, help="a new folder, apart from --out, for task files and keys")
    m.add_argument("--python", help="the python3 the checks run (default: the worker's, found on PATH)")
    c = commands.add_parser("check", help="run the hidden cases on the code in the current folder")
    c.add_argument("--key", type=Path, required=True)
    one = commands.add_parser("case", help="run one hidden case (the check runs this in a child process)")
    one.add_argument("--key", type=Path, required=True)
    one.add_argument("--case", required=True)
    one.add_argument("--root", type=Path, required=True)
    one.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "make":
        written = make(args.seed, args.more, args.only, args.out.expanduser(), args.keys.expanduser(), args.python)
        print(f"Wrote {len(written)} tasks; the list is {args.keys.expanduser() / 'tasks.txt'}. Note the seed in your "
              "study note; anyone who has it can regenerate the answers.")
        return 0
    if args.command == "explain":
        print(json.dumps(explain(args.seed, args.more, args.only), indent=1))
        return 0
    if args.command == "case":
        passed, message = run_case(json.loads(args.key.read_text()), args.case, args.root.resolve())
        args.out.write_text(json.dumps({"passed": passed, "message": message}))
        return 0
    return check(args.key, Path.cwd())


if __name__ == "__main__":
    sys.exit(main())

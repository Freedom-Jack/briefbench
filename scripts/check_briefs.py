"""A factual check of the briefs written for `missing-fact/1` tasks, in place of a person's fidelity review
(claims/plans/questions-first-2.md, "Fidelity"). Standard library and briefbench only.

    uv run python scripts/check_briefs.py --experiment NAME [--dry-run]

Round 1's fidelity review asked a person to judge each brief as its requester would. With generated tasks answered by
the stand-in requester nobody holds that role, so its questions became a reading test. This check reads facts instead:
the task file (which group or start month the request means, and the facts the stand-in could give), the prompt, the
skill's questions with the stand-in's answers, and the brief. It uses no model and asks no one. A brief fails it when:

- dropped: it leaves out a detail the request gave: the data file's path, report.md, the line `Answer: <rate>` with
  its example `Answer: 12.3%`, "one decimal" or "percentage"; the group or start month, when the prompt states it or
  the stand-in gave it; or the key words of another fact the stand-in gave, such as "Thursday" or "no charts";
- changed: it leaves out the purpose the prompt gives, such as the retention offer and the proposal;
- added: it gives a number or a month that neither the prompt, the stand-in's answers nor the data's description
  gives, such as a rate worked out in advance, a row count, today's date or the data's months misstated; it names a
  group beside its column ("the Team plan") when the request's group was never given; or it passes a skipped question
  on: a paragraph says that something is unsaid, undecided or open ("I haven't said", "not specified", "still open")
  and shares a word with a question the stand-in skipped, or, when the request's own group or month never reached the
  rewriter, any paragraph says so.

It reads no outcome, diff or other arm. It checks the briefs of arm B that the experiment's fidelity policy chooses
and that have no review yet, and, unless --dry-run, writes each result to the log as a `fidelity` line marked
"by": "check", which `score` counts as it counts a review. Run it once all the rule's trials are in, before reading
the score. It refuses an experiment whose log already has lines from another version of this check.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import re
import sys
from pathlib import Path

from briefbench import experiment, score
from briefbench.log import append, data_dir, header, read_entries
from briefbench.presets import secret_values
from briefbench.tasks import load

HERE = Path(__file__).resolve()
_spec = importlib.util.spec_from_file_location("missing_fact", HERE.parent / "materials" / "missing_fact.py")
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)
CHECK_SHA256 = hashlib.sha256(HERE.read_bytes()).hexdigest()
GENERATOR_SHA256 = hashlib.sha256(Path(_spec.origin).read_bytes()).hexdigest()

# What every prompt of the set asks for, besides the data file's path, as the brief must still ask for it.
NEEDED = (("report.md", r"report\.md"), ("the line Answer: <rate>", r"answer: <[^>\n]{1,40}>"),
          ("its example 12.3%", r"\b12\.3\s?%"), ("one decimal", r"\b(?:one|1|single) decimal"),
          ("percentage", r"\bpercent"))
# The purpose each kind of prompt gives, by domain and kind of fact: the start of each word the brief keeps.
PURPOSE = {("churn", "group"): ("retention", "proposal"), ("churn", "window"): ("pric", "board"),
           ("returns", "group"): ("packag", "review"), ("returns", "window"): ("polic", "review"),
           ("delays", "group"): ("handl", "planning meeting"), ("delays", "window"): ("rout", "planning meeting")}
# The facts that don't change the answer: when the stand-in gave one, what the brief keeps, one word of each group.
SPECIFICS = {"The proposal goes to the leadership meeting on Thursday.": (("leadership",), ("thursday",)),
             "Keep the write-up short: a page is plenty.": (("page",),),
             "The review is with the operations team next week.": (("operations",), ("next week",)),
             "A short summary is enough; no charts needed.": (("chart",),),
             "The planning meeting is on the 20th.": (("20th",),),
             "Plain numbers are fine; it doesn't need to look polished.": (("polish", "plain numbers"),)}
NAMES = {"na": ("north america",), "eu": ("europe",), "apac": ("asia-pacific", "asia pacific"),
         "latam": ("latin america",)}           # a region code written out names the same group
# The words a brief puts beside a group's value when it names the group, by column.
NOUNS = {"plan": ("plan",), "region": ("region",), "channel": ("channel", "through", "via"),
         "category": ("categor", "order"), "warehouse": ("warehouse",), "carrier": ("carrier", "carried", "shipment"),
         "origin_hub": ("hub",), "package_size": ("package", "parcel", "size")}
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
SHORT = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10,
         "Nov": 11, "Dec": 12}
DATA_MONTHS = {1, 6}               # the data's description: "between January and June 2026"
ANY_NUMBER = {1.0, 100.0}          # "1 decimal", "1 page", "step 1", "x 100": no fact either way
# A date that shows the data's format, with what follows it up to the end of the clause: "formatted like 2026-04".
FORMAT = re.compile(r"(?:\blike|\be\.g\.,?|\bi\.e\.,?|\bform(?:at(?:ted)?)?(?:\s+(?:as|like|of))?|YYYY-MM,?"
                    r"(?:\s+form(?:at)?)?)[\s`'\"(:]*2026-\d\d[^)\n.;]*", re.I)
# Words that say the request left something unsaid, undecided or open.
OPEN = re.compile("|".join((
    r"(?:\b(?:have|has|had|did|does|was|were|is|are)|'ve)(?:n't|\s+not)\s+(?:yet\s+)?(?:been\s+)?(?:said|say|specified|"
    r"specify|stated|state|decided|decide|settled|settle|confirmed|confirm|answered|answer|mentioned|mention|given|"
    r"give|told|tell|clarified|clarify|defined|define|indicated|indicate|chosen|choose|picked|pick|named|name|"
    r"determined|resolved)\b",
    r"\b(?:i|we)\s+(?:do|did)(?:n't|\s+not)\s+know\b",
    r"\b(?:nobody|no one)\s+(?:has|have|had)\s+(?:yet\s+)?(?:said|decided|settled|specified|confirmed|stated|chosen|"
    r"named)\b",
    r"\bnot\s+(?:yet\s+)?(?:specified|stated|answered|decided|settled|confirmed|given|defined|resolved|determined|"
    r"known|named)\b",
    r"\b(?:unspecified|unanswered|undecided|unsettled|unconfirmed|unresolved|undetermined|unstated|tbd)\b",
    r"\b(?:is|are|remains?)\s+unknown\b", r"\bopen\s+(?:question|choice|point|issue|decision|item)s?\b",
    r"\b(?:still|left|remains?|remained|stays?|is|are|was|were|kept)\s+open\b",
    r"\b(?:gave|got|had|has|have|with)\s+no\s+answer\b", r"\bnone\s+(?:was\s+)?given\b",
    r"\bno\s+(?:\w+\s+){1,2}(?:(?:was|were|is|are|has been|have been)\s+)?specified\b",
    r"\bto be (?:decided|confirmed|determined|settled)\b")), re.I)
# Words too common to tie a paragraph to a question.
STOP = frozenset("""about above after again also another because been before being below between both could does doing
during each every from further have having here into itself just like more most other ours over same should some such
than that their them then there these they this those through under until very want were what when where whether which
while will with would your yours file files data column columns rows rate rates report value values table number
numbers example""".split())


def plain(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'")


def months(text: str, examples: bool = False) -> set[int]:
    """The months a text names, by name, short name or as 2026-MM. A May that starts a sentence counts only before a
    year, a number, a range or a stop, so that the verb doesn't; unless examples, dates that show the data's format
    ("formatted like 2026-04, 2026-05") don't count, nor does the rest of their clause."""
    text = text if examples else FORMAT.sub(" ", text)
    found = {int(m.group(1)) for m in re.finditer(r"\b2026-(0[1-9]|1[0-2])\b", text)}
    for n, name in enumerate(MONTHS, 1):
        for m in re.finditer(rf"\b{name}\b", text):
            before = text[:m.start()].rstrip(" \t*-`(\"'")
            if name != "May" or (before and before[-1] not in ".!?:\n") or re.match(
                    r"May(?:\s+2026|\s*\d|\s*[-–—]|\s+(?:to|through|and|or|onwards?)\b|[,.)]|\s*$)", text[m.start():]):
                found.add(n)
    return found | {n for name, n in SHORT.items() if re.search(rf"\b{name}\b", text)}


def numbers(text: str) -> set[float]:
    """The numbers a text gives, leaving out list markers, dates in the data's form (see months), 1 and 100."""
    text = re.sub(r"\b2026-\d\d(?:-\d\d)?\b", " ", text)
    text = re.sub(r"(?m)^[ \t>]*(?:\*\*|__)?(?:[-*+]|\d+[.)])[ \t]+", " ", text)
    text = re.sub(r"\(\d+\)|'\d\d\b", " ", text)                    # (1) in a sentence; '26 for the year
    return {float(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?!\w)", text.replace(",", ""))} - ANY_NUMBER


def stems(text: str) -> set[str]:
    """The text's words of four letters or more, other than common ones, cut to five letters: months and month."""
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4 and w not in STOP}


def names_group(flat: str, level: str) -> bool:
    return bool(re.search(rf"\b{re.escape(level)}s?\b", flat)) or any(n in flat for n in NAMES.get(level, ()))


def groups_named(domain: dict, flat: str) -> list[str]:
    """The groups a brief names: a value next to its column's word ("the Team plan", "plan = team"), or a region
    written out, when the brief doesn't list all of that column's values, which only describes the data."""
    found = []
    for column, (levels, _weights, _doc, phrase) in domain["factors"].items():
        if not phrase:
            continue
        named = [lv for lv in levels if any(n in flat for n in NAMES.get(lv, ())) or any(re.search(
            rf"\b{lv}s?\b(?:\W+\w+){{0,2}}?\W+{noun}|\b{noun}\w*(?:\W+\w+){{0,2}}?\W+{lv}s?\b", flat)
            for noun in NOUNS[column])]
        if named and not all(names_group(flat, lv) for lv in levels):
            found += named
    return found


def passed_on(brief: str, prompt: str, answers: str, skipped: list[str], central: bool = False) -> list[str]:
    """The words that say something is unsaid or open, in a paragraph that, with the next one, shares a word with a
    question the stand-in skipped, beyond the words of the prompt and the answers. None when it skipped none. With
    central, when the request's own group or month never reached the rewriter, such words count anywhere: the
    question that was skipped is then about the prompt's own words ("one group of our customers")."""
    topic = set().union(*map(stems, skipped)) - stems(prompt) - stems(answers)
    paragraphs = [p for p in re.split(r"\n\s*\n", plain(brief)) if p.strip()]
    found = set()
    for n, paragraph in enumerate(paragraphs):
        hits = {re.sub(r"\s+", " ", m.group(0).lower()) for m in OPEN.finditer(paragraph)}
        if hits and skipped and (central or stems(" ".join(paragraphs[n:n + 2])) & topic):
            found |= hits
    return sorted(found)


def fact_of(task: dict) -> tuple[dict, str, list]:
    """The task's domain, the kind of its fact (group or window) and the fact, read from its goal."""
    said = task["goal"].split(". ", 1)[-1]
    for domain in mf.DOMAINS:
        groups = [["group", column, level] for column, spec in domain["factors"].items() if spec[3] for level in spec[0]]
        for kind, facts in (("group", groups), ("window", [["from", m] for m in range(1, 7)])):
            for fact in facts:
                if domain[kind][2].format(**mf.wording(domain, fact)) == said:
                    return domain, kind, fact
    raise ValueError(f"task {task['id']}: its goal names no fact of set {mf.SET}")


def findings(task: dict, prompt: str, asked: list[dict], brief: str) -> dict[str, list[str]]:
    """What fails in one brief, by fidelity question: {"added": [...], "dropped": [...], "changed": [...]}. asked
    holds the skill's questions, each with the numbers of the facts the stand-in chose ("facts"); none is a skip."""
    domain, kind, fact = fact_of(task)
    said = task["goal"].split(". ", 1)[-1]
    chosen = sorted({n for q in asked for n in q.get("facts") or [] if 1 <= n <= len(task["facts"])})
    given = [task["facts"][n - 1] for n in chosen]
    answers, flat = " ".join(given), re.sub(r"\s+", " ", plain(brief).replace("`", "")).lower()
    known = task["stratum"] == "no-gap" or said in given        # the request's group or month reached the rewriter
    out = {"added": [], "dropped": [], "changed": []}
    for label, pattern in ((f"data/{domain['file']}", re.escape(f"data/{domain['file']}")), *NEEDED):
        if not re.search(pattern, flat):
            out["dropped"].append(f"no {label}")
    if known and kind == "group" and not names_group(flat, fact[2]):
        out["dropped"].append(f"the group {fact[2]!r} is missing")
    if known and kind == "window" and fact[1] not in months(brief, examples=True):
        out["dropped"].append(f"the start month {MONTHS[fact[1] - 1]} is missing")
    for given_fact in given:
        out["dropped"] += [f"{' or '.join(words)!r}, from an answer, is missing"
                           for words in SPECIFICS.get(given_fact, ()) if not any(w in flat for w in words)]
    out["changed"] += [f"the purpose word {word!r}... is missing" for word in PURPOSE[(domain["name"], kind)]
                       if not re.search(rf"\b{word}", flat)]
    allowed = months(prompt) | months(answers) | DATA_MONTHS | (set(range(1, 7)) if kind == "window" and known else set())
    if extra := sorted(months(brief) - allowed):
        out["added"].append("months nobody gave: " + ", ".join(MONTHS[n - 1] for n in extra))
    if extra := sorted(numbers(brief) - numbers(prompt) - numbers(answers) - numbers(domain["readme"])):
        out["added"].append("numbers nobody gave: " + ", ".join(f"{x:g}" for x in extra))
    if not known and kind == "group" and (named := groups_named(domain, flat)):
        out["added"].append("names a group, which nobody gave: " + ", ".join(named))
    skipped = [q["q"] for q in asked if not q.get("facts")]
    if hits := passed_on(brief, prompt, answers, skipped, central=not known):
        out["added"].append("passes a skipped question on: " + "; ".join(repr(h) for h in hits))
    return out


def main(argv=None, stdout=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--experiment", required=True, help="the experiment whose briefs the check reads")
    parser.add_argument("--dry-run", action="store_true", help="print what fails, and write nothing to the log")
    args = parser.parse_args(argv)
    stdout = stdout or sys.stdout
    exp = experiment.load(args.experiment, os.environ)
    path = data_dir(os.environ) / "log.jsonl"
    entries = read_entries(path) if path.exists() else []
    if other := {e.get("check_sha256") for e in score._lines(exp, entries)
                 if e.get("kind") == "fidelity" and e.get("by") == "check"} - {CHECK_SHA256}:
        print(f"experiment {exp['name']} already has fidelity lines from another version of this check "
              f"({', '.join(sorted(str(s)[:12] for s in other))}), so its briefs would be checked two ways.",
              file=sys.stderr)
        return 2
    queue, why = score.review_queue(exp, entries)
    if why:
        print(why, file=sys.stderr)
        return 2
    checked = []
    for trial in queue:
        task = load(Path(trial["task"]["source"]["file"]))
        if task["set"] != mf.SET or task["generator_sha256"] != GENERATOR_SHA256:
            print(f"task {task['id']} isn't from set {mf.SET} made by this generator ({GENERATOR_SHA256[:12]}...), "
                  "so this check doesn't apply to it.", file=sys.stderr)
            return 2
        asked = [q for q in trial["task"]["questions"] if q["skill"] == exp["b"]["spec"]]
        checked.append((trial, findings(task, trial["task"]["prompt"], asked, trial["prompts"]["b"])))
    failed = [(t, found) for t, found in checked if any(found.values())]
    for trial, found in failed:
        print(f"Trial {trial['id'][:8]} ({trial['task']['source'].get('stratum')}): "
              + "; ".join(f"{key}: {', '.join(whys)}" for key, whys in found.items() if whys), file=stdout)
    if not args.dry_run:
        for trial, found in checked:
            append(path, header("fidelity") | {
                "experiment": exp["name"], "experiment_created": exp.get("created"), "trial": trial["id"], "side": "b",
                **{key: bool(whys) for key, whys in found.items()}, "by": "check", "check_sha256": CHECK_SHA256,
                "reasons": [f"{key}: {why}" for key, whys in found.items() for why in whys]}, secret_values(os.environ))
    counts = {key: sum(bool(found[key]) for _t, found in checked) for key in ("added", "dropped", "changed")}
    policy = exp.get("fidelity_policy") or {"max_unfaithful": 0}
    print(f"Checked {len(checked)} brief{'s' if len(checked) != 1 else ''}: {len(failed)} failed (added "
          f"{counts['added']}, dropped {counts['dropped']}, changed {counts['changed']}); the experiment allows "
          f"{policy['max_unfaithful']}." + (" Nothing was written (--dry-run)." if args.dry_run else
                                             " Each result is a fidelity line in the log."), file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

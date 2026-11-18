"""scripts/check_briefs.py: the factual check of briefs written for missing-fact/1 tasks, offline. Briefs are built
from generated tasks, faithful ones and ones with a planted slip; the bench runs through fake agent CLIs."""
import importlib.util
import io
import json
import os
import re
from pathlib import Path

import pytest

from briefbench import cli, experiment, score
from briefbench.log import read_entries
from briefbench.tasks import load

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_briefs", ROOT / "scripts" / "check_briefs.py")
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)
mf = cb.mf
PERIOD = "Should the rate cover every signup month in the file, or only a recent period?"     # skipped below


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """Twelve task files, six of each kind, from all three domains and both kinds of fact."""
    folder = tmp_path_factory.mktemp("made")
    return [load(p) for p in mf.make(seed=8, gap=6, complete=6, out=folder / "repos", keys=folder / "keys")]


def synth(domain, fact, stratum="no-gap"):
    """A task with a chosen fact, built with the generator's own wording; it has no data, which the check never reads."""
    plan = {"domain": domain, "fact_kind": "group" if fact[0] == "group" else "window", "kind": stratum,
            "fact": list(fact), "template_seed": 1}
    rate = mf.domain_of(plan)["rate"]
    return {"id": "t-synth", "stratum": stratum, "prompt": mf.prompt(plan), "facts": mf.facts(plan),
            "goal": f"Report the {rate} the requester means. {mf.said(plan)}"}


def key(task):
    """The number of the task's own fact among its facts, as the stand-in would choose it."""
    return task["facts"].index(task["goal"].split(". ", 1)[1]) + 1


def faithful(task, give_key=True, fillers=(), skipped=()):
    """A brief that only restates the request and the answers: the prompt, then each fact the stand-in gave. The
    questions in skipped are asked and skipped."""
    chosen = ([key(task)] if give_key else []) + [task["facts"].index(f) + 1 for f in fillers]
    brief = task["prompt"] + "".join(f"\n\n{task['facts'][n - 1]}" for n in chosen)
    return [{"q": "Which one?", "a": "", "facts": chosen}] + [{"q": q, "a": "", "facts": []} for q in skipped], brief


def failing(task, asked, brief):
    return {k: v for k, v in cb.findings(task, task["prompt"], asked, brief).items() if v}


def of_kind(made, stratum, kind):
    return next(t for t in made if t["stratum"] == stratum and cb.fact_of(t)[1] == kind)


def test_the_tables_follow_the_generator():
    assert cb.GENERATOR_SHA256 == mf.hashlib.sha256((ROOT / "scripts" / "materials" / "missing_fact.py")
                                                    .read_bytes()).hexdigest()
    fillers = {f for d in mf.DOMAINS for f in d["fillers"]}
    assert set(cb.SPECIFICS) == fillers
    for filler, groups in cb.SPECIFICS.items():
        assert all(any(w in filler.lower() for w in words) for words in groups)
    for d in mf.DOMAINS:
        assert set(cb.NOUNS) >= {c for c, spec in d["factors"].items() if spec[3]}
        for kind in ("group", "window"):
            for prompt in d[kind][:2]:                      # the gap and the no-gap wording
                assert all(re.search(rf"\b{w}", prompt.lower()) for w in cb.PURPOSE[(d["name"], kind)])


def test_a_brief_that_keeps_the_request_and_the_answers_passes(made):
    for task in made:
        assert not failing(task, *faithful(task, skipped=[PERIOD]))
        assert not failing(task, *faithful(task, fillers=task["facts"]))       # every fact given and kept
        if task["stratum"] == "gap":
            assert not failing(task, *faithful(task, give_key=False))           # the gap left as the draft has it


def test_a_dropped_detail_fails(made):
    task = of_kind(made, "no-gap", "group")
    asked, brief = faithful(task)
    for cut in ("such as `Answer: 12.3%`", "report.md", "with one decimal", "`Answer: <rate>`"):
        assert "dropped" in failing(task, asked, brief.replace(cut, ""))
    level = cb.fact_of(task)[2][2]
    assert "dropped" in failing(task, asked, re.sub(rf"(?i)\b{level}\b", "other", brief))
    window = of_kind(made, "no-gap", "window")
    month = mf.MONTHS[cb.fact_of(window)[2][1] - 1]
    asked, brief = faithful(window)
    assert "dropped" in failing(window, asked, brief.replace(month, "a later month"))
    filler = next(f for f in task["facts"] if f in cb.SPECIFICS)
    asked, brief = faithful(task, fillers=[filler])
    assert "dropped" in failing(task, asked, brief.replace(filler, "There is a deadline."))


@pytest.mark.parametrize("domain, fact, old, new", [
    ("churn", ("group", "region", "na"), "customers in NA", "customers in North America"),
    ("churn", ("group", "channel", "referral"), "through referral", "through referrals"),
    ("churn", ("group", "plan", "team"), "with one decimal", "to a single decimal place"),
    ("churn", ("group", "plan", "team"), "`Answer: <rate>`", "`Answer: <churn rate>`"),
    ("churn", ("group", "plan", "team"), "such as `Answer: 12.3%`", "such as 12.3%"),
    ("churn", ("from", 5), "from May 2026 on", "from that month on. Start month: May."),
    ("churn", ("from", 5), "from May 2026 on", "from the change. May onward is the period"),
    ("churn", ("from", 4), "from April 2026 on", "from April '26 on")])
def test_a_detail_said_another_way_is_kept(domain, fact, old, new):
    task = synth(domain, fact)
    asked, brief = faithful(task)
    assert old in brief
    assert not failing(task, asked, brief.replace(old, new))


def test_a_missing_purpose_is_a_changed_request(made):
    task = of_kind(made, "no-gap", "group")
    domain, kind, _fact = cb.fact_of(task)
    word = {"retention": "retention offer", "packag": "packaging", "handl": "handle"}[cb.PURPOSE[(domain["name"],
                                                                                                 kind)][0]]
    asked, brief = faithful(task)
    assert set(failing(task, asked, brief.replace(word, "plan"))) == {"changed"}


def test_an_added_number_month_or_group_fails(made):
    group, window = of_kind(made, "no-gap", "group"), of_kind(made, "no-gap", "window")
    for task, extra in ((group, "So far it looks like about 24.2%."), (group, "The file has 2,350 rows."),
                        (group, "The data covers January to May 2026."), (window, "Today is 2026-11-11."),
                        (window, "Use only the last 3 months.")):
        asked, brief = faithful(task)
        assert set(failing(task, asked, f"{brief}\n\n{extra}")) == {"added"}, extra
    gap = synth("churn", ("group", "plan", "team"), "gap")
    asked, brief = faithful(gap, give_key=False)
    for extra in ("Use the Team plan customers.", "Count rows where plan = pro.", "Use the customers in North America."):
        assert set(failing(gap, asked, f"{brief}\n\n{extra}")) == {"added"}, extra
    for extra in ("The plan column holds basic, pro and team.", "It goes to the leadership team.",
                  "Treat blank or NA values as missing."):
        assert not failing(gap, asked, f"{brief}\n\n{extra}"), extra


@pytest.mark.parametrize("extra", ["I haven't said which months the rate should cover.", "Time period: not specified.",
                                   "Two choices are still open, so make them yourself:\n- which signup months count.",
                                   "Open question: the period.", "Nobody has decided whether recent signups count.",
                                   "The start month is unknown.", "I’ve not said whether recent signups count.",
                                   "The request doesn't say which months count; decide.",
                                   "Which months count is to be decided.", "No period specified, so pick one."])
def test_passing_a_skipped_question_on_fails(made, extra):
    task = of_kind(made, "no-gap", "group")
    asked, brief = faithful(task, skipped=[PERIOD])
    assert set(failing(task, asked, f"{brief}\n\n{extra}")) == {"added"}
    asked, brief = faithful(task)                       # with no question skipped, the new rule says nothing
    assert not failing(task, asked, f"{brief}\n\n{extra}")


def test_when_the_group_itself_was_skipped_any_such_words_count():
    task = synth("churn", ("group", "plan", "team"), "gap")
    asked, brief = faithful(task, give_key=False)            # the one question asked is skipped
    for extra in ("The request doesn't say which group the offer is for; pick one.", "Group: none given."):
        assert set(failing(task, asked, f"{brief}\n\n{extra}")) == {"added"}, extra
    assert not failing(task, asked, brief)


@pytest.mark.parametrize("extra", ["Recent signups may not have had time to churn yet.",
                                   "The month column is formatted like 2026-04.", "Give it to 1 decimal place.",
                                   "1. Read the file.\n2. Count the rows that match.", "**1. Request**",
                                   "report.md should give (1) the rate and (2) how you got it.",
                                   "The month column holds values like 2026-01, 2026-02 and so on.",
                                   "The month column is YYYY-MM (e.g. 2026-03 is March 2026).",
                                   "The month column is in YYYY-MM form (2026-03).",
                                   "If the data is unclear or ambiguous, say how you handled it.",
                                   "How you lay out the report is up to you.",
                                   "I haven't said how to define churn; use the README's definition.",
                                   "When asked who it is for, I gave the group above.",
                                   "I asked only for this one rate.", "No other restriction was given, so use the whole "
                                   "group.", "The exact day isn't given in the file.",
                                   "Rows with a blank value are skipped."])
def test_words_that_are_neither_facts_nor_a_passed_on_question_pass(made, extra):
    task = of_kind(made, "no-gap", "group")
    asked, brief = faithful(task, skipped=[PERIOD])
    assert not failing(task, asked, f"{brief}\n\n{extra}")


def bench(argv, cwd):
    return cli.run(argv, stdin=io.StringIO(""), stderr=io.StringIO(), cwd=cwd)


def checked(dry=False):
    out = io.StringIO()
    code = cb.main(["--experiment", "exp", *(["--dry-run"] if dry else [])], stdout=out)
    return code, out.getvalue()


def init(cwd, cap="400"):
    return bench(["init", "exp", "--a", "original", "--b", f"skill:{ROOT / 'variants' / 'questions-first-2'}",
                  "--worker", "claude-code", "--worker-model", "", "--rewriter", "claude-code", "--rewriter-model", "",
                  "--judge", "none", "--cap", cap, "--rule", "fixed:10", "--net-min", "0", "--scoring", "check",
                  "-y"], cwd)


def test_each_brief_gets_a_fidelity_line_that_score_counts(agents, tmp_path, monkeypatch):
    files = mf.make(seed=3, gap=1, complete=1, out=tmp_path / "repos", keys=tmp_path / "keys")
    assert init(tmp_path) == 0
    monkeypatch.setenv("FAKE_ANSWERER", "none")              # no fact given: the fake brief is the prompt itself
    for path in files:
        assert bench(["ab", "--task", str(path)], tmp_path) == 0
    assert checked(dry=True)[1].startswith("Checked 2 briefs: 0 failed")
    exp = experiment.load("exp", os.environ)
    log = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    assert not [e for e in read_entries(log) if e["kind"] == "fidelity"]               # a dry run writes nothing
    assert checked() == (0, "Checked 2 briefs: 0 failed (added 0, dropped 0, changed 0); the experiment allows 0. "
                            "Each result is a fidelity line in the log.\n")
    lines = [e for e in read_entries(log) if e["kind"] == "fidelity"]
    assert len(lines) == 2 and all(e["by"] == "check" and e["check_sha256"] == cb.CHECK_SHA256 and e["side"] == "b"
                                   and not (e["added"] or e["dropped"] or e["changed"]) for e in lines)
    summary = score.summary(exp, read_entries(log))
    assert summary["fidelity_review"]["waiting"] == 0 and summary["fidelity_review"]["unfaithful"] == 0
    monkeypatch.setenv("FAKE_ANSWERER", "first")             # a fact given that the fake brief leaves out
    assert bench(["ab", "--task", str(files[0])], tmp_path) == 0
    code, shown = checked()
    assert code == 0 and "Checked 1 brief: 1 failed" in shown and "dropped" in shown         # only the new brief
    assert not any(word in shown for word in ("passed", "wins", " tie", "diff"))            # no outcome at all
    summary = score.summary(exp, read_entries(log))
    assert summary["fidelity_review"]["unfaithful"] == 1
    assert "1 of the briefs chosen for review failed your fidelity review, and at most 0 may" \
        in summary["verdict"]["blocked_by"]
    with log.open("a") as f:                                 # a line from another version of the check
        f.write(json.dumps(lines[0] | {"id": "x", "check_sha256": "0" * 64}) + "\n")
    assert checked()[0] == 2


def test_tasks_of_another_set_are_refused(agents, repo, tmp_path):
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"format": 1, "id": "t-001", "set": "demo/1", "repo": str(repo), "facts": ["F."],
                                "prompt": "Make result.txt", "type": "analysis", "goal": "Say it.",
                                "check": "true"}))
    assert init(tmp_path, cap="50") == 0
    assert bench(["ab", "--task", str(path)], tmp_path) == 0
    assert checked()[0] == 2

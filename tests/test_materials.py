"""scripts/materials/planted_cause.py and scripts/run_tasks.py: generated tasks with a planted answer (set 4), their
checker, and the unattended runner, offline. Every file is written under a temporary folder."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.log import read_entries
from briefbench.tasks import load

ROOT = Path(__file__).resolve().parent.parent


def peek(monkeypatch, tmp_path, command):
    """A peeking fake worker prints `command` as if it had run it. The command comes from a file: a variable naming a
    denied folder never reaches the worker's environment."""
    (tmp_path / "peek.txt").write_text(command)
    monkeypatch.setenv("FAKE_PEEK_FILE", str(tmp_path / "peek.txt"))


def script(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


planted = script("planted_cause", "scripts/materials/planted_cause.py")
runner = script("run_tasks", "scripts/run_tasks.py")


@pytest.fixture
def made(tmp_path):
    """A set of six tasks, three of each kind: (the keys folder, each task's plan by task id)."""
    keys = tmp_path / "keys"
    planted.make(seed=3, wrong=3, right=3, out=tmp_path / "repos", keys=keys)
    return keys, {t["name"]: t for t in (planted.plan(3, kind, k) for kind, k in planted.order(3, 3))}


@pytest.fixture(scope="module")
def big(tmp_path_factory):
    """Twelve tasks, six of each kind, from all three domains: (the task files, each task's plan by id).
    Made once for the module, since the analyses below read every file; making a set touches neither HOME nor the
    data folder."""
    folder = tmp_path_factory.mktemp("big")
    files = planted.make(seed=8, wrong=6, right=6, out=folder / "repos", keys=folder / "keys")
    plans = {t["name"]: t for t in (planted.plan(8, kind, k) for kind, k in planted.order(6, 6))}
    return files, plans


def task_files(keys):
    return [keys / line for line in (keys / "tasks.txt").read_text().split()]


def domain(plan):
    return planted.domain_of(plan)


def grade(task_file, answer):
    task = json.loads(task_file.read_text())
    repo = Path(task["repo"])
    report = repo / "report.md"
    if answer is None:
        report.unlink(missing_ok=True)
    else:
        report.write_text(f"# Findings\n\nThe numbers.\n\n**Main driver:** `{answer}`\n")
    code = subprocess.run(task["check"], shell=True, cwd=repo, capture_output=True, text=True).returncode
    report.unlink(missing_ok=True)
    return code


def verdict(task_file, answer, folder):
    """The checker's verdict in this process, which is quicker than its command: 0 right, 1 wrong."""
    (folder / "report.md").write_text(f"# Findings\n\nThe numbers.\n\n**Main driver:** `{answer}`\n")
    with contextlib.redirect_stdout(io.StringIO()):
        return planted.check(task_file.parent / "key.json", folder / "report.md")


def rows(repo, name):
    with (repo / "data" / name).open() as f:
        return list(csv.DictReader(f))


def read(repo, d, tables):
    """What an analyst reads from the repo's files in `tables` ("main", "log" or both): the outcome per entity, and a
    yes/no flag per entity for each candidate cause, by the name the data gives it: each level of each main-table
    column ("plan = team"), and having at least one of an event that some entities have and others don't
    ("payment_failed"). With the log alone, the entities and the outcome come from the log."""
    main, log = rows(repo, d["file"]), rows(repo, "events.csv")
    who = {}
    for r in log:
        who.setdefault(r["event"], set()).add(r[d["id"]])
    if "main" in tables:
        ids, outcome = [r[d["id"]] for r in main], [r[d["outcome"]] == "yes" for r in main]
    else:
        ids = sorted({r[d["id"]] for r in log})
        outcome = [i in who[d["outcome_event"][0]] for i in ids]
    flags = {}
    if "main" in tables:
        for column in main[0]:
            if column not in (d["id"], d["date"], d["outcome"]):
                for value in {r[column] for r in main}:
                    flags[f"{column} = {value}"] = [r[column] == value for r in main]
    if "log" in tables:
        for event, seen in who.items():
            if event != d["outcome_event"][0] and len(seen) < len(ids):
                flags[event] = [i in seen for i in ids]
    return flags, outcome


def split_gap(flag, outcome, within=None):
    """The outcome rate's gap with and without the flag; with `within`, averaged over both sides of that flag."""
    if within is not None:
        return sum(split_gap([f for f, w in zip(flag, within) if w == side],
                             [o for o, w in zip(outcome, within) if w == side]) * within.count(side) / len(within)
                   for side in (True, False))
    yes, no = [o for f, o in zip(flag, outcome) if f], [o for f, o in zip(flag, outcome) if not f]
    return sum(yes) / len(yes) - sum(no) / len(no)


def strongest(flags, outcome):
    gaps = {name: split_gap(flag, outcome) for name, flag in flags.items()}
    return max(gaps, key=gaps.get), gaps


def name_of(d, item):
    """The name the analyses above give a planted item."""
    kind, name = item
    return name if kind == "event" else f"{name} = {d['factors'][name][2]}"


def pointed(task):
    """The tables the prompt points at, read from the prompt as an analyst would."""
    return ("log",) if "data/events.csv" in task["prompt"] else ("main",)


def test_a_set_is_a_list_of_task_files_with_a_planted_answer(made):
    keys, plans = made
    files = task_files(keys)
    assert len(files) == 6 and (keys / "planted_cause.py").is_file()
    assert all(name.startswith("t") and len(name) == 13 for name in plans)              # opaque names
    assert sorted(t["kind"] for t in plans.values()) == ["belief-right"] * 3 + ["belief-wrong"] * 3
    for path in files:
        task, plan = load(path), plans[json.loads(path.read_text())["id"]]
        d = domain(plan)
        assert task["type"] == "analysis" and task["stratum"] == plan["kind"] and task["set"] == planted.SET
        assert subprocess.run(["git", "status", "--porcelain"], cwd=task["repo"], capture_output=True,
                              text=True).stdout == ""
        kind, name = plan["belief"]
        stated = d["events"][name][1] if kind == "event" else d["factors"][name][3]
        assert stated in task["prompt"]                                               # the prompt states the belief
        table = "events.csv" if kind == "event" else d["file"]                        # and points at its table only
        assert f"data/{table}" in task["prompt"] and task["prompt"].count(".csv") == 1
        assert any(word in task["prompt"] for word in ("size it", "numbers", "quantify"))      # only to size it
        assert task["prompt"].endswith(planted.FORMAT_LINE) and "the most" not in task["prompt"]
        readme = (Path(task["repo"]) / "README.md").read_text()        # every file, column and event, documented
        names = [d["file"], "events.csv", d["id"], d["date"], d["outcome"], *d["factors"], *d["events"],
                 *(r[0] for r in d["routine"]), d["outcome_event"][0]]
        assert all(f"`{n}`" in readme or f"data/{n}" in readme for n in names)
        assert sorted(p.name for p in (Path(task["repo"]) / "data").iterdir()) == sorted([d["file"], "events.csv"])
        key = json.loads((path.parent / "key.json").read_text())
        assert all(len(h) == 64 for h in key["accepted"]) and plan["cause"][1] not in json.dumps(key["accepted"])
        repo = Path(task["repo"])                   # nothing in the repo names the task, its seed or its key
        assert keys not in repo.parents and "seed" not in "".join(f.read_text() for f in repo.rglob("*.md"))


def test_the_cause_is_a_column_and_the_belief_names_it_or_the_decoy():
    """The cause is always a level of a main-table column, fixed before any event, and the decoy an event that travels
    with it. A right belief names the cause and points at the main table; a wrong one names the decoy and points at
    the log. So the pointed table holds the cause only when the belief is right."""
    plans = [planted.plan(5, kind, k) for kind, k in planted.order(6, 6)]
    assert {t["domain"] for t in plans} == {"churn", "returns", "delays"}
    for t in plans:
        assert t["cause"][0] == "factor" and t["decoy"][0] == "event"
        assert t["belief"] == (t["cause"] if t["kind"] == "belief-right" else t["decoy"])
        assert t["file"] == ("events.csv" if t["kind"] == "belief-wrong" else domain(t)["file"])
    kinds = [kind for kind, _ in planted.order(20, 10)]            # the kinds spread evenly through the list
    assert kinds[:3].count("belief-wrong") == 2 and kinds[:15].count("belief-right") == 5


def test_a_full_analysis_recovers_the_key(big):
    """Read both tables: the candidate with the largest gap in the outcome rate is the planted cause. It holds once
    the data is split by the runner-up, whose own gap goes, and the check passes a report that names it."""
    files, plans = big
    for path in files:
        plan, task = plans[json.loads(path.read_text())["id"]], load(path)
        d = domain(plan)
        flags, outcome = read(Path(task["repo"]), d, ("main", "log"))
        top, gaps = strongest(flags, outcome)
        assert top == name_of(d, plan["cause"])
        column = top.split(" = ")[0]
        second = max((n for n in gaps if n.split(" = ")[0] != column), key=gaps.get)
        assert second == name_of(d, plan["decoy"])
        assert split_gap(flags[top], outcome, flags[second]) > 0.15
        assert abs(split_gap(flags[second], outcome, flags[top])) < 0.05
        assert grade(path, top) == 0


def test_the_pointed_table_alone_names_the_decoy_when_the_belief_is_wrong(big):
    """An analysis of only the table the prompt points at names the stated belief: the decoy when the belief is wrong,
    which the check fails, and the cause when it is right, which it passes, so confirming a right belief never needs
    the other table."""
    files, plans = big
    for path in files:
        plan, task = plans[json.loads(path.read_text())["id"]], load(path)
        d = domain(plan)
        top, _gaps = strongest(*read(Path(task["repo"]), d, pointed(task)))
        assert top == name_of(d, plan["belief"])
        assert grade(path, top) == (1 if plan["kind"] == "belief-wrong" else 0)


def test_the_decoy_only_looks_like_a_cause(big):
    """The decoy shows the outcome at least 7 points more often, less than the cause does, and within each side of
    the cause nothing beyond sampling noise."""
    files, plans = big
    for path in files:
        plan, task = plans[json.loads(path.read_text())["id"]], load(path)
        d = domain(plan)
        flags, outcome = read(Path(task["repo"]), d, ("main", "log"))
        cause, decoy = flags[name_of(d, plan["cause"])], flags[name_of(d, plan["decoy"])]
        assert split_gap(cause, outcome) > split_gap(decoy, outcome) >= 0.07
        for side in (True, False):
            pick = [c == side for c in cause]
            part = [o for o, p in zip(outcome, pick) if p]
            marked = [m for m, p in zip(decoy, pick) if p]
            rate = sum(part) / len(part)
            error = (rate * (1 - rate) * (1 / max(1, sum(marked)) + 1 / max(1, len(marked) - sum(marked)))) ** 0.5
            assert abs(split_gap(marked, part)) < 3 * error + 1e-9


def test_the_log_agrees_with_the_main_table(made):
    """The outcome's event marks exactly the rows whose outcome is yes, and comes after the row's other events. Every
    row has its first event on its first day, every event falls in its window, the log runs oldest first, and nothing
    is dated after the export."""
    keys, plans = made
    for path in task_files(keys):
        task = json.loads(path.read_text())
        d, repo = domain(plans[task["id"]]), Path(task["repo"])
        main = {r[d["id"]]: r for r in rows(repo, d["file"])}
        log = rows(repo, "events.csv")
        assert [r["day"] for r in log] == sorted(r["day"] for r in log)
        days = {}
        for r in log:
            days.setdefault(r[d["id"]], []).append((date.fromisoformat(r["day"]), r["event"]))
        assert set(days) == set(main)
        first, ending = d["routine"][0][0], d["outcome_event"][0]
        for eid, seen in days.items():
            assert seen[0][1] == first and seen == sorted(seen, key=lambda s: s[0])
            assert (main[eid][d["outcome"]] == "yes") == any(event == ending for _, event in seen)
            start = seen[0][0]
            own = main[eid][d["date"]]
            if d["date"] == "ship_week":
                assert start.isocalendar()[1] == int(own[-2:]) or start == date(2026, 1, 1)
            else:
                assert start.month == int(own[-2:]) and start.day <= 28
            assert max(day for day, _ in seen) <= start + timedelta(days=d["span"] - 1) < date(2026, 10, 1)
            if any(event == ending for _, event in seen):
                stop = next(day for day, event in seen if event == ending)
                assert all(day <= stop for day, event in seen if event not in (ending, "delivered"))


def test_the_checker_takes_the_planted_cause_and_nothing_else(made, tmp_path):
    """The last `Main driver:` line counts, and what its words name before any explanation, read whole, however it is
    spelt: the column alone, with its table or its blamed level, the level's own words, or the belief's. The decoy
    event, after the event column or not, the other events and columns, the outcome, the decoy named first, and a
    sentence that only starts with the cause's words, such as a denial, fail."""
    keys, plans = made
    for path in task_files(keys):
        plan = plans[json.loads(path.read_text())["id"]]
        d = domain(plan)
        main = Path(d["file"]).stem
        (_, cause), (_, decoy) = plan["cause"], plan["decoy"]
        assert grade(path, name_of(d, plan["cause"])) == 0 and grade(path, name_of(d, plan["decoy"])) == 1
        assert grade(path, None) == 1                                                 # the command, and no report
        _levels, _weights, bad, belief, _doc, phrases = d["factors"][cause]
        for answer in (cause, f"{cause} = {bad}", f"{cause} ({bad})", f"{cause}_{bad}", f"{main}.{cause}",
                       f"{d['file']}: {cause}", f"data/{d['file']} - {cause}", f"the {cause} column", f"has_{cause}",
                       belief.split(":")[0], *(p.replace("_", " ") for p in phrases),
                       *([bad] if bad not in ("yes", "no") else []), f"{cause} == '{bad}'", f"{cause}, then {decoy}",
                       f"{cause} and its link to {decoy}", f"{cause} in {d['file']}", f"{cause} - drives it"):
            assert verdict(path, answer, tmp_path) == 0, answer
        columns = [c for c in d["factors"] if c != cause]
        _doc, decoy_belief, decoy_phrases = d["events"][decoy]
        for answer in (decoy, f"event = {decoy}", f"event_type: {decoy}", f"events.{decoy}", f"events.csv: {decoy}",
                       f"{decoy} events", f"has_{decoy}", decoy_belief.split(":")[0],
                       *(p.replace("_", " ") for p in decoy_phrases), *d["events"], *columns,
                       *(d["factors"][c][3].split(":")[0] for c in columns), d["outcome"], d["outcome_event"][0],
                       d["id"], "events.csv", d["file"], f"{decoy} and {cause}", f"{decoy}, {cause}",
                       f"{cause} is fine; it is {decoy}", f"{cause} does not matter; {decoy} does", f"not {cause}",
                       "unclear"):
            if answer != cause:
                assert verdict(path, answer, tmp_path) == 1, answer
    report = tmp_path / "plural.md"                       # a `Main drivers:` line counts too, by its first name
    report.write_text(f"Main drivers: {cause}, {decoy}\n")
    with contextlib.redirect_stdout(io.StringIO()):
        assert planted.check(path.parent / "key.json", report) == 0


def test_each_candidate_has_names_of_its_own():
    """In every domain, no two candidate causes share a name, and none is named like the outcome, the id, a routine
    event or the log, so the check can't take one for another."""
    for d in planted.DOMAINS:
        items = [("event", e) for e in d["events"]] + [("factor", f) for f in d["factors"]]
        taken = {planted.canon(n) for n in (d["outcome"], d["id"], d["date"], d["outcome_event"][0], "events.csv",
                                            "events", "event", d["file"], *(r[0] for r in d["routine"]))}
        seen = set()
        for item in items:
            names = set(planted.names(d, item))
            assert not names & seen and not names & taken, (d["name"], item, names & (seen | taken))
            seen |= names


def test_explain_gives_each_answer_in_the_order_of_the_list(made):
    keys, plans = made
    items = planted.explain(3, 3, 3)
    assert [i["id"] for i in items] == [json.loads(f.read_text())["id"] for f in task_files(keys)]
    for item in items:
        plan = plans[item["id"]]
        assert item["stratum"] == plan["kind"] and item["driver"].startswith(plan["cause"][1])
        assert item["pointed_at"] == f"data/{plan['file']}" and item["decoy"].startswith(plan["decoy"][1])


def test_a_seed_gives_the_same_set_whatever_your_git_settings(tmp_path, monkeypatch):
    planted.make(seed=5, wrong=1, right=1, out=tmp_path / "r1", keys=tmp_path / "k1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Someone Else")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "else@example.invalid")
    planted.make(seed=5, wrong=1, right=1, out=tmp_path / "r2", keys=tmp_path / "k2")
    for one, two in zip(task_files(tmp_path / "k1"), task_files(tmp_path / "k2")):
        a, b = json.loads(one.read_text()), json.loads(two.read_text())
        assert a["commit"] == b["commit"] and a["prompt"] == b["prompt"] and a["id"] == b["id"]


def test_make_never_writes_into_an_existing_set(made, tmp_path):
    keys, _ = made
    checker = (keys / "planted_cause.py").read_bytes()
    for out, into in ((tmp_path / "repos", tmp_path / "new-keys"), (tmp_path / "new-repos", keys),
                      (tmp_path / "x", tmp_path / "x" / "keys")):
        with pytest.raises(SystemExit):
            planted.make(seed=4, wrong=1, right=0, out=out, keys=into)
    with pytest.raises(SystemExit):
        planted.make(seed=4, wrong=0, right=0, out=tmp_path / "none", keys=tmp_path / "none-keys")
    assert (keys / "planted_cause.py").read_bytes() == checker


def freeze(repo, tmp_path):
    tip = tmp_path / "tip.md"
    tip.write_text("Treat my belief as a hypothesis.\n")
    return cli.run(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "claude-code", "--worker-model",
                    "", "--judge", "none", "--cap", "50", "--rule", "fixed:10", "--net-min", "0.05", "--scoring",
                    "check", "-y"], stdin=io.StringIO(""), stderr=io.StringIO(), cwd=repo)


def log():
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def test_the_runner_runs_each_task_once_and_picks_up_where_it_stopped(agents, made, repo, tmp_path):
    keys, _ = made
    assert freeze(repo, tmp_path) == 0
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp", "--limit", "2"]) == 0
    assert [e["kind"] for e in log()] == ["trial", "trial"]
    assert all(e["decision"]["check_tie"] == "both_failed" for e in log())     # the fake worker writes no report
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp", "--limit", "1"]) == 0
    ids = [e["task"]["source"]["id"] for e in log()]
    assert len(ids) == 3 and len(set(ids)) == 3                                # the third task, not a repeat


def test_noise_checks_and_trials_keep_their_own_tasks(agents, made, repo, tmp_path):
    keys, _ = made
    freeze(repo, tmp_path)
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp", "--aa", "--limit", "2"]) == 0
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp", "--limit", "2"]) == 0
    entries = log()
    assert [e["kind"] for e in entries] == ["aa", "aa", "trial", "trial"]
    assert [e["task"]["source"]["id"] for e in entries[:2]] == [e["task"]["source"]["id"] for e in entries[2:]]


def test_the_runner_stops_at_a_failed_step_and_retries_it_once_next_time(agents, made, repo, tmp_path, monkeypatch):
    keys, _ = made
    freeze(repo, tmp_path)
    monkeypatch.setenv("FAKE_WORKER", "limit")
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 4
    assert [e["kind"] for e in log()] == ["failed"]                            # stopped after one: no more usage
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 4
    first = log()[0]["task"]["source"]["id"]
    assert [e["task"]["source"]["id"] for e in log()] == [first, first]       # the same task, retried once
    monkeypatch.setenv("FAKE_WORKER", "good")
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp", "--limit", "1"]) == 0
    entries = log()
    assert entries[-1]["kind"] == "trial" and entries[-1]["task"]["source"]["id"] != first   # failed twice: moved on


def test_the_runner_stops_when_an_arm_names_the_data_folder(agents, made, repo, tmp_path, monkeypatch):
    keys, _ = made
    freeze(repo, tmp_path)
    monkeypatch.setenv("FAKE_WORKER", "peek")
    peek(monkeypatch, tmp_path, f"ls {os.environ['BRIEFBENCH_HOME']}/keys")
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 1
    assert len(log()) == 1 and log()[0]["arms"]["a"]["looked_outside"]


def test_the_runner_stops_once_the_rule_has_all_its_trials(agents, made, repo, tmp_path):
    """The tasks after the first N are reserves: they run only in place of a task that failed twice."""
    keys, _ = made
    freeze(repo, tmp_path)
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json"
    path.write_text(json.dumps(json.loads(path.read_text()) | {"rule": {"kind": "fixed", "trials": 2, "alpha": 0.05,
                                                                         "net_min": 0}}))      # 2 trials, to be quick
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 0
    assert [e["kind"] for e in log()] == ["trial", "trial"] and "All 2 trials the rule tests are in" in out.getvalue()


def test_the_runner_stops_at_a_halfway_look_where_b_is_not_ahead(agents, made, repo, tmp_path):
    """The fake worker writes no report, so every trial ties, and B is not ahead at the look after 2 trials."""
    keys, _ = made
    tip = tmp_path / "tip.md"
    tip.write_text("Treat my belief as a hypothesis.\n")
    assert cli.run(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "claude-code",
                    "--worker-model", "", "--judge", "none", "--cap", "50", "--rule", "fixed:10", "--net-min", "0",
                    "--futility-at", "2", "--scoring", "check", "-y"],
                   stdin=io.StringIO(""), stderr=io.StringIO(), cwd=repo) == 0
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 0
    assert [e["kind"] for e in log()] == ["trial", "trial"] and "The halfway look" in out.getvalue()


def test_the_runner_runs_a_frozen_list_only_in_its_order(agents, made, repo, tmp_path):
    keys, _ = made
    tip = tmp_path / "tip.md"
    tip.write_text("Treat my belief as a hypothesis.\n")
    assert cli.run(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "claude-code",
                    "--worker-model", "", "--judge", "none", "--cap", "50", "--rule", "fixed:10", "--net-min", "0",
                    "--scoring", "check", "--strata", "belief-wrong,belief-right", "--stage", "test", "--plan-commit",
                    "abc1234", "--tasks", str(keys / "tasks.txt"), "--seed-source", "a test", "-y"],
                   stdin=io.StringIO(""), stderr=io.StringIO(), cwd=repo) == 0
    frozen = json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json").read_text())["materials"]
    assert frozen["set"] == planted.SET and frozen["generator_sha256"] == frozen["checker_sha256"]
    assert frozen["generator_sha256"] == hashlib.sha256((keys / "planted_cause.py").read_bytes()).hexdigest()
    reordered = keys / "reordered.txt"
    reordered.write_text("".join(reversed((keys / "tasks.txt").read_text().splitlines(keepends=True))))
    with contextlib.redirect_stderr(io.StringIO()):
        assert runner.main([str(reordered), "--experiment", "exp"]) == 2
    assert log() == [] and agents() == []
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp", "--limit", "1"]) == 0
    assert log()[0]["task"]["source"]["stratum"] in ("belief-wrong", "belief-right")


def test_the_runner_needs_a_check_scored_experiment(agents, made, repo, tmp_path):
    keys, _ = made
    tip = tmp_path / "tip.md"
    tip.write_text("x\n")
    cli.run(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "codex", "--worker-model", "",
             "--judge", "none", "--cap", "50", "-y"], stdin=io.StringIO(""), stderr=io.StringIO(), cwd=repo)
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 2 and log() == [] and agents() == []

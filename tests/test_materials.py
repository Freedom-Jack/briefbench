"""scripts/materials/planted_cause.py and scripts/run_tasks.py: generated tasks with a planted answer, their checker,
and the unattended runner, offline. Every file is written under a temporary folder."""
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
    """A set of six tasks: (the keys folder, the answers by task id)."""
    keys = tmp_path / "keys"
    planted.make(seed=3, count=6, out=tmp_path / "repos", keys=keys)
    return keys, {t["id"]: t for t in planted.explain(3, 6)}


def task_files(keys):
    return [keys / line for line in (keys / "tasks.txt").read_text().split()]


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


def test_a_set_is_a_list_of_task_files_with_a_planted_answer(made):
    keys, answers = made
    files = task_files(keys)
    assert len(files) == 6 and (keys / "planted_cause.py").is_file()
    assert all(t["id"].startswith("t") and len(t["id"]) == 13 for t in answers.values())    # opaque names
    assert sorted(t["stratum"] for t in answers.values()) == ["belief-right"] * 3 + ["belief-wrong"] * 3
    for path in files:
        task, truth = load(path), answers[json.loads(path.read_text())["id"]]
        assert task["type"] == "analysis" and "Main driver: <column name>" in task["prompt"]
        assert task["stratum"] == truth["stratum"]                 # the kind of task, for score to test apart
        assert subprocess.run(["git", "status", "--porcelain"], cwd=task["repo"], capture_output=True,
                              text=True).stdout == ""
        domain = next(d for d in planted.DOMAINS if d["name"] == truth["domain"])
        stated = (domain["sources"][truth["belief"]]["belief"] if truth["belief"] in domain["sources"]
                  else domain["factors"][truth["belief"]][3])
        assert stated.split(":")[0] in task["prompt"]                              # the prompt states the belief
        assert f"data/{domain['file']}" in task["prompt"] and ".csv" not in task["prompt"].replace(domain["file"], "")
        readme = (Path(task["repo"]) / "README.md").read_text()                     # every file is documented
        assert all(f"data/{name}" in readme for name in [domain["file"], *(s["file"] for s in domain["sources"].values())])
        key = json.loads((path.parent / "key.json").read_text())
        assert all(len(h) == 64 for h in key["accepted"]) and truth["driver"] not in json.dumps(key["accepted"])
        repo = Path(task["repo"])                   # nothing in the repo names the task, its seed or its key
        assert keys not in repo.parents and "seed" not in "".join(f.read_text() for f in repo.rglob("*.md"))


def verdict(task_file, answer, folder):
    """The checker's verdict in this process, which is quicker than its command: 0 right, 1 wrong."""
    (folder / "report.md").write_text(f"# Findings\n\nThe numbers.\n\n**Main driver:** `{answer}`\n")
    with contextlib.redirect_stdout(io.StringIO()):
        return planted.check(task_file.parent / "key.json", folder / "report.md")


def test_the_checker_takes_the_planted_driver_and_nothing_else(made, tmp_path):
    """The last `Main driver:` line counts, and what its words name before any explanation, read whole, however it is
    spelt: the column alone, with its table or its level, the table or file, the bad level, the belief's own words or a
    plain phrase. The decoy, the other event table, the decoy named first, and a sentence that only starts with the
    driver's words, such as a denial, fail."""
    keys, answers = made
    for path in task_files(keys):
        truth = answers[json.loads(path.read_text())["id"]]
        domain = next(d for d in planted.DOMAINS if d["name"] == truth["domain"])
        driver, decoy, main = truth["driver"], truth["decoy"], Path(domain["file"]).stem
        noise = next(name for name in domain["sources"] if name != driver)
        source, other = domain["sources"][driver], domain["sources"][noise]
        stem, other_stem, phrase = Path(source["file"]).stem, Path(other["file"]).stem, source["phrases"][0]
        assert grade(path, driver) == 0 and grade(path, decoy) == 1 and grade(path, None) == 1     # the command
        for answer in (f"{driver} (by far)", f"{driver} = {source['bad']}", f"{driver}, then {decoy}", source["bad"],
                       stem, f"data/{source['file']}", f"{stem}.{driver}", f"has_{phrase}", f"the {driver}",
                       source["belief"].split(":")[0], f"{main} with {phrase.replace('_', ' ')}",
                       *(p.replace("_", " ") for p in source["phrases"]),
                       f"{phrase.replace('_', ' ')} in {source['file']}", f"{driver} - {source['bad']} drives it"):
            assert verdict(path, answer, tmp_path) == 0, answer
        for answer in (f"the {decoy}", f"{main}.{decoy}", f"{decoy} and {driver}", f"{decoy}, {driver}", noise,
                       f"{other_stem}.{noise}", other_stem, other["bad"], *(p.replace("_", " ") for p in other["phrases"]),
                       other["belief"].split(":")[0], f"has_{other['phrases'][0]}", domain["outcome"], domain["id"],
                       f"{stem} are fine; it is the {decoy}", f"{source['bad']} to identify a single driver",
                       f"{phrase.replace('_', ' ')} do not matter; {decoy} does", f"{stem} speed"):
            assert verdict(path, answer, tmp_path) == 1, answer
    report = tmp_path / "plural.md"                       # a `Main drivers:` line counts too, by its first name
    report.write_text(f"Main drivers: {driver}, {decoy}\n")
    with contextlib.redirect_stdout(io.StringIO()):
        assert planted.check(path.parent / "key.json", report) == 0


def rows(repo, name):
    with (repo / "data" / name).open() as f:
        return list(csv.DictReader(f))


def test_every_event_falls_in_its_rows_span(made):
    """Events come within 90 days of a signup, 14 days of an order, or on the days a shipment is on the road, which
    the weather table lists one by one and the scans keep to. Nothing is dated after the export."""
    keys, answers = made
    for path in task_files(keys):
        task = json.loads(path.read_text())
        repo = Path(task["repo"])
        domain = next(d for d in planted.DOMAINS if d["name"] == answers[task["id"]]["domain"])
        own = {r[domain["id"]]: r[domain["date"]] for r in rows(repo, domain["file"])}
        days = {}
        for name, source in domain["sources"].items():
            for r in rows(repo, source["file"]):
                days.setdefault(name, {}).setdefault(r[domain["id"]], []).append(date.fromisoformat(r[source["date"]]))
        for name, source in domain["sources"].items():
            for eid, seen in days[name].items():
                if domain["date"] == "ship_week":
                    week = int(own[eid][-2:])
                    first, last = max(date.fromisocalendar(2026, week, 1), date(2026, 1, 1)), \
                        date.fromisocalendar(2026, week, 7)
                else:
                    first, last = date(2026, int(own[eid][-2:]), 1), date(2026, int(own[eid][-2:]), 28)
                assert first <= min(seen) and max(seen) <= last + timedelta(days=domain["span"] - 1) < date(2026, 10, 1)
                assert seen == sorted(seen)
                if source.get("daily"):
                    assert seen == [seen[0] + timedelta(days=k) for k in range(len(seen))]
        if domain["name"] == "delays":
            assert len(days["weather"]) == len(own)                     # every shipment has its days on the road
            assert all(set(seen) <= set(days["weather"][eid]) for eid, seen in days["scan_result"].items())


def test_the_decoy_only_looks_like_a_cause(made):
    """In the main table the decoy's bad level shows more of the outcome and stands out from the other columns. Joined
    with its event table, the real driver's gap is the larger one, and within each side of it the decoy shows
    nothing beyond sampling noise."""
    keys, answers = made
    for path in task_files(keys):
        truth = answers[json.loads(path.read_text())["id"]]
        repo = Path(json.loads(path.read_text())["repo"])
        domain = next(d for d in planted.DOMAINS if d["name"] == truth["domain"])
        main = list(csv.DictReader((repo / "data" / domain["file"]).open()))
        source = domain["sources"][truth["driver"]]
        events = csv.DictReader((repo / "data" / source["file"]).open())
        hit = {r[domain["id"]] for r in events if r[truth["driver"]] == source["bad"]}
        outcome, decoy_bad = domain["outcome"], domain["factors"][truth["decoy"]][2]

        def gap(rows, inside):
            """The outcome rate's gap between rows where `inside` holds and the rest, and its standard error."""
            yes = [r[outcome] == "yes" for r in rows if inside(r)]
            no = [r[outcome] == "yes" for r in rows if not inside(r)]
            p = (sum(yes) + sum(no)) / (len(yes) + len(no))
            return sum(yes) / len(yes) - sum(no) / len(no), (p * (1 - p) * (1 / len(yes) + 1 / len(no))) ** 0.5

        is_decoy = lambda r: r[truth["decoy"]] == decoy_bad
        driver_gap, decoy_gap = gap(main, lambda r: r[domain["id"]] in hit)[0], gap(main, is_decoy)[0]
        assert driver_gap > decoy_gap > 0.04
        for other, (levels, *_rest) in domain["factors"].items():   # the decoy stands out in the main table
            if other != truth["decoy"]:
                assert all(gap(main, lambda r: r[other] == level)[0] < decoy_gap for level in levels)
        for side in (True, False):
            split = [r for r in main if (r[domain["id"]] in hit) == side]
            difference, error = gap(split, is_decoy)
            assert abs(difference) < 3 * error             # no effect of its own, up to sampling noise


def test_a_seed_gives_the_same_set_whatever_your_git_settings(tmp_path, monkeypatch):
    planted.make(seed=5, count=2, out=tmp_path / "r1", keys=tmp_path / "k1")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Someone Else")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "else@example.invalid")
    planted.make(seed=5, count=2, out=tmp_path / "r2", keys=tmp_path / "k2")
    for one, two in zip(task_files(tmp_path / "k1"), task_files(tmp_path / "k2")):
        a, b = json.loads(one.read_text()), json.loads(two.read_text())
        assert a["commit"] == b["commit"] and a["prompt"] == b["prompt"] and a["id"] == b["id"]


def test_make_never_writes_into_an_existing_set(made, tmp_path):
    keys, _ = made
    checker = (keys / "planted_cause.py").read_bytes()
    for out, into in ((tmp_path / "repos", tmp_path / "new-keys"), (tmp_path / "new-repos", keys),
                      (tmp_path / "x", tmp_path / "x" / "keys")):
        with pytest.raises(SystemExit):
            planted.make(seed=4, count=1, out=out, keys=into)
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

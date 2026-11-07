"""scripts/materials/planted_cause.py and scripts/run_tasks.py: generated tasks with a planted answer, their checker,
and the unattended runner, offline. Every file is written under a temporary folder."""
import csv
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.log import read_entries
from briefbench.tasks import load

ROOT = Path(__file__).resolve().parent.parent


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
        assert subprocess.run(["git", "status", "--porcelain"], cwd=task["repo"], capture_output=True,
                              text=True).stdout == ""
        belief = next(d for d in planted.DOMAINS if d["name"] == truth["domain"])["factors"]
        assert belief[truth["belief"]][3].split(":")[0] in task["prompt"]          # the prompt states the belief
        key = json.loads((path.parent / "key.json").read_text())
        assert all(len(h) == 64 for h in key["accepted"]) and truth["driver"] not in json.dumps(key["accepted"])
        repo = Path(task["repo"])                   # nothing in the repo names the task, its seed or its key
        assert keys not in repo.parents and "seed" not in "".join(f.read_text() for f in repo.rglob("*.md"))


def test_the_checker_takes_the_planted_driver_and_nothing_else(made):
    """The last `Main driver:` line counts, and its first named column: the column alone, with its level, or the
    level when it isn't yes or no. Naming the decoy first, or two columns joined by "and", fails."""
    keys, answers = made
    for path in task_files(keys):
        truth = answers[json.loads(path.read_text())["id"]]
        driver, decoy = truth["driver"], truth["decoy"]
        level = next(d for d in planted.DOMAINS if d["name"] == truth["domain"])["factors"][driver][2]
        assert grade(path, driver) == 0 and grade(path, f"{driver} (by far)") == 0
        assert grade(path, f"{driver} = {level}") == 0 and grade(path, f"{driver}, then {decoy}") == 0
        assert grade(path, level) == (1 if level in ("yes", "no") else 0)
        assert grade(path, decoy) == 1 and grade(path, f"{decoy} and {driver}") == 1
        assert grade(path, f"{decoy}, {driver}") == 1 and grade(path, None) == 1


def test_the_decoy_only_looks_like_a_cause(made):
    """In a plain breakdown the decoy's bad level shows more of the outcome; within each side of the real driver
    it shows almost none, and the real driver's gap is the larger one."""
    keys, answers = made
    for path in task_files(keys):
        truth = answers[json.loads(path.read_text())["id"]]
        [data] = (Path(json.loads(path.read_text())["repo"]) / "data").glob("*.csv")
        rows = list(csv.DictReader(data.open()))
        outcome = list(rows[0])[-1]
        domain = next(d for d in planted.DOMAINS if d["name"] == truth["domain"])
        bad = {f: domain["factors"][f][2] for f in (truth["driver"], truth["decoy"])}

        def gap(rows, factor):
            """The outcome rate's gap between the bad level and the rest, and its standard error."""
            yes = [r[outcome] == "yes" for r in rows if r[factor] == bad[factor]]
            no = [r[outcome] == "yes" for r in rows if r[factor] != bad[factor]]
            p = (sum(yes) + sum(no)) / (len(yes) + len(no))
            return sum(yes) / len(yes) - sum(no) / len(no), (p * (1 - p) * (1 / len(yes) + 1 / len(no))) ** 0.5

        assert gap(rows, truth["driver"])[0] > gap(rows, truth["decoy"])[0] > 0.04
        for side in (True, False):
            split = [r for r in rows if (r[truth["driver"]] == bad[truth["driver"]]) == side]
            difference, error = gap(split, truth["decoy"])
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
    return cli.run(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "codex", "--worker-model",
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
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 1
    assert len(log()) == 1 and log()[0]["arms"]["a"]["looked_outside"]


def test_the_runner_needs_a_check_scored_experiment(agents, made, repo, tmp_path):
    keys, _ = made
    tip = tmp_path / "tip.md"
    tip.write_text("x\n")
    cli.run(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "codex", "--worker-model", "",
             "--judge", "none", "--cap", "50", "-y"], stdin=io.StringIO(""), stderr=io.StringIO(), cwd=repo)
    assert runner.main([str(keys / "tasks.txt"), "--experiment", "exp"]) == 2 and log() == [] and agents() == []

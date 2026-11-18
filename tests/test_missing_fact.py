"""scripts/materials/missing_fact.py: requests with a missing fact, for the skill's first growth round, offline. Every
file is written under a temporary folder."""
import contextlib
import csv
import importlib.util
import io
import json
import subprocess
from pathlib import Path

import pytest

from briefbench.tasks import load

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("missing_fact", ROOT / "scripts" / "materials" / "missing_fact.py")
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """Twelve tasks, six of each kind, from all three domains and both kinds of fact: (task files, plans by id).
    Making a set touches neither HOME nor the data folder."""
    folder = tmp_path_factory.mktemp("made")
    files = mf.make(seed=8, gap=6, complete=6, out=folder / "repos", keys=folder / "keys")
    return files, {t["name"]: t for t in (mf.plan(8, kind, k) for kind, k in mf.order(6, 6))}


def each(made):
    files, plans = made
    for path in files:
        task = load(path)
        yield path, task, plans[task["id"]], mf.domain_of(plans[task["id"]])


def grade(path, answer):
    """The check's command on a report whose last Answer line gives `answer`: 0 when it passes."""
    task = json.loads(path.read_text())
    repo = Path(task["repo"])
    (repo / "report.md").write_text(f"# Rates\n\nThe numbers.\n\n**Answer:** {answer}\n")
    try:
        return subprocess.run(task["check"], shell=True, cwd=repo, capture_output=True, text=True).returncode
    finally:
        (repo / "report.md").unlink()


def rows(task, domain):
    with (Path(task["repo"]) / "data" / domain["file"]).open() as f:
        return list(csv.DictReader(f))


def rate(rows, outcome, keep=lambda r: True):
    picked = [r for r in rows if keep(r)]
    return 100 * sum(r[outcome] == "yes" for r in picked) / len(picked)


def keeps(domain, fact):
    """The rows a fact keeps, read as an analyst reads it from the requester's words."""
    if fact[0] == "group":
        return lambda r: r[fact[1]] == fact[2]
    return lambda r: int(r[domain["date"]][-2:]) >= fact[1]


def test_a_set_is_a_list_of_task_files_with_the_requesters_facts(made):
    files, plans = made
    assert sorted(t["kind"] for t in plans.values()) == ["gap"] * 6 + ["no-gap"] * 6
    assert {(t["domain"], t["fact_kind"]) for t in plans.values()} >= {(d["name"], f) for d in mf.DOMAINS
                                                                        for f in ("group", "window")}
    for path, task, plan, domain in each(made):
        assert task["type"] == "analysis" and task["stratum"] == plan["kind"] and task["set"] == mf.SET
        assert task["prompt"].endswith(mf.FORMAT_LINE.format(rate=domain["rate"]))
        assert mf.said(plan) in task["facts"] and len(task["facts"]) == 3                 # the fact and two fillers
        assert sorted(task["facts"]) == sorted([mf.said(plan), *domain["fillers"]])
        assert mf.said(plan) in task["goal"]                     # the goal names the fact; it never reaches an arm
        assert subprocess.run(["git", "status", "--porcelain"], cwd=task["repo"], capture_output=True,
                              text=True).stdout == ""


def test_a_gap_prompt_leaves_the_fact_out_and_a_complete_one_states_it(made):
    for path, task, plan, domain in each(made):
        named = mf.wording(domain, plan["fact"])
        words = named.get("group") or named["month"]
        if plan["kind"] == "gap":
            assert words not in task["prompt"] and ("one group" in task["prompt"] or "one kind" in task["prompt"]
                                                    or "since the change" in task["prompt"])
        else:
            assert words in task["prompt"]


def test_the_repo_never_depends_on_the_missing_fact(made):
    """The data is drawn before the fact, and the README names no decision or change: the same task with any other
    fact its data allows has byte-for-byte the same files, so no repo can give its fact away."""
    for path, task, plan, domain in each(made):
        others = [f for f in mf.facts_for(domain, mf.tables(plan), plan["fact_kind"]) if list(f) != plan["fact"]]
        for other in others:
            assert mf.tables(plan | {"fact": list(other)}) == mf.tables(plan)
        readme = (Path(task["repo"]) / "README.md").read_text().lower()
        assert not any(word in readme for word in ("offer", "packaging", "pricing", "policy", "routing", "change"))
        files = sorted(p.relative_to(task["repo"]).as_posix() for p in Path(task["repo"]).rglob("*")
                       if p.is_file() and ".git" not in p.parts)
        assert files == ["README.md", f"data/{domain['file']}"]


def test_the_check_passes_only_with_the_fact(made):
    """With the fact, an analysis of the table gives the planted rate, which the check passes in common spellings.
    Without it, the rate over everyone, any other group, month or start month fails."""
    for path, task, plan, domain in each(made):
        table = rows(task, domain)
        right = rate(table, domain["outcome"], keeps(domain, plan["fact"]))
        assert abs(right - plan["expected"]) < 1e-3                         # the key keeps four decimals
        for answer in (f"{right:.1f}%", f"{right:.1f}", f"{right / 100:.4f}", f"about {right:.1f}% of them",
                       f"{right:.1f}% (n = {len(table)})", f"Q2: {right:.1f}%", f"{right:.2f} percent"):
            assert grade(path, answer) == 0, answer
        found = mf.rates(domain, mf.tables(plan))
        assert grade(path, f"{found[('all',)]:.1f}%") == 1                    # everyone: the plain guess
        for key in mf.rivals(found, plan["fact_kind"]):
            if list(key) != plan["fact"]:
                assert grade(path, f"{found[key]:.1f}%") == 1, key
        assert grade(path, "n/a: which group?") == 1


def test_the_group_is_never_the_one_that_stands_out_most(made):
    for path, task, plan, domain in each(made):
        if plan["fact_kind"] == "group":
            found = mf.rates(domain, mf.tables(plan))
            groups = {k: abs(v - found[("all",)]) for k, v in found.items() if k[0] == "group"}
            assert tuple(plan["fact"]) != max(groups, key=groups.get)
            assert domain["factors"][plan["fact"][1]][3]                       # a column with more than two levels


def test_the_last_answer_line_counts(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("Answer: 10.0%\n\nOn second thought:\n\nAnswer: 20.0%\n")
    key = tmp_path / "key.json"
    key.write_text(json.dumps({"expected": 20.0, "tolerance": mf.TOLERANCE}))
    with contextlib.redirect_stdout(io.StringIO()):
        assert mf.check(key, report) == 0
        report.write_text("The rate is 20.0%.\n")                              # no Answer line
        assert mf.check(key, report) == 1
        assert mf.check(key, tmp_path / "missing.md") == 1


def test_explain_gives_each_answer_in_the_order_of_the_list(made):
    files, plans = made
    items = mf.explain(8, 6, 6)
    assert [i["id"] for i in items] == [json.loads(f.read_text())["id"] for f in files]
    assert all(i["nearest_rival"] >= 1 and abs(i["expected"] - i["overall"]) >= 3 for i in items)


def test_a_seed_gives_the_same_set_and_a_set_is_never_added_to(tmp_path):
    one = mf.make(seed=5, gap=1, complete=1, out=tmp_path / "r1", keys=tmp_path / "k1")
    two = mf.make(seed=5, gap=1, complete=1, out=tmp_path / "r2", keys=tmp_path / "k2")
    for a, b in zip(one, two):
        a, b = json.loads(a.read_text()), json.loads(b.read_text())
        assert a["commit"] == b["commit"] and a["prompt"] == b["prompt"] and a["facts"] == b["facts"]
    for out, keys in ((tmp_path / "r1", tmp_path / "k3"), (tmp_path / "r3", tmp_path / "k1"),
                      (tmp_path / "x", tmp_path / "x" / "keys")):
        with pytest.raises(SystemExit):
            mf.make(seed=4, gap=1, complete=0, out=out, keys=keys)
    with pytest.raises(SystemExit):
        mf.make(seed=4, gap=0, complete=0, out=tmp_path / "none", keys=tmp_path / "none-keys")

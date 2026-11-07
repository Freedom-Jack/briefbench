"""Unattended trials: init --scoring check, the fixed rule's declared threshold, and ab --task, through fake agent
CLIs (tests/fake_agent.py). The fake worker writes "brief" into result.txt when its prompt holds BRIEF."""
import io
import json
import os
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.log import read_entries

SKILL = Path(__file__).resolve().parents[1] / "skills" / "brief"


def bench(argv, typed="", cwd=None):
    err = io.StringIO()
    return cli.run(argv, stdin=io.StringIO(typed), stderr=err, cwd=cwd), err.getvalue()


def entries():
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def frozen():
    return json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json").read_text())


@pytest.fixture
def tip(tmp_path):
    path = tmp_path / "tip.md"
    path.write_text("BRIEF: treat my belief as a hypothesis.\n")
    return path


def init(cwd, b, *extra):
    return bench(["init", "exp", "--a", "original", "--b", b, "--worker", "codex", "--worker-model", "",
                  "--judge", "none", "--cap", "50", "-y", *extra], cwd=cwd)


def task_file(tmp_path, repo, check="grep -q brief result.txt", **fields):
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"format": 1, "id": "t-001", "set": "demo/1", "repo": str(repo),
                                "prompt": "Make result.txt say what it is", "type": "analysis",
                                "goal": "Say what it is", "check": check, **fields}))
    return path


def test_check_scoring_needs_a_fixed_rule_and_a_declared_threshold(agents, repo, tip):
    code, err = init(repo, f"snippet:{tip}", "--scoring", "check", "--net-min", "0.05")
    assert code == 2 and "--rule fixed:N" in err and not (Path(os.environ["BRIEFBENCH_HOME"]) / "experiments").exists()
    code, err = init(repo, f"snippet:{tip}", "--scoring", "check", "--rule", "fixed:30")
    assert code == 2 and "declare --net-min" in err


def test_a_threshold_belongs_to_a_fixed_rule(agents, repo, tip):
    assert init(repo, f"snippet:{tip}", "--net-min", "0.05")[0] == 2
    assert init(repo, f"snippet:{tip}", "--rule", "fixed:30", "--alpha", "0")[0] == 2
    code, err = init(repo, f"snippet:{tip}", "--rule", "fixed:30", "--net-min", "0.05", "--alpha", "0.025",
                     "--scoring", "check")
    assert code == 0, err
    exp = frozen()
    assert exp["rule"] == {"kind": "fixed", "trials": 30, "alpha": 0.025, "net_min": 0.05}
    assert exp["scoring"] == "check" and "Scored by the check alone" in err


def test_an_experiment_records_pick_scoring_by_default(agents, repo, tip):
    assert init(repo, f"snippet:{tip}")[0] == 0
    assert frozen()["scoring"] == "pick"


def test_a_task_file_runs_a_trial_with_no_questions(agents, repo, tip, tmp_path):
    assert init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")[0] == 0
    path = task_file(tmp_path, repo)
    code, err = bench(["ab", "--task", str(path)], "", cwd=tmp_path)       # no input: nothing may be asked
    assert code == 0, err
    [t] = entries()
    assert t["kind"] == "trial" and t["decision"]["by"] == "check" and t["decision"]["winner"] == "b"
    assert t["task"]["type"] == "analysis" and t["task"]["answers"]["why"] == "Say what it is"
    assert t["task"]["source"]["id"] == "t-001" and t["task"]["source"]["set"] == "demo/1"
    assert len(t["task"]["source"]["sha256"]) == 64 and t["task"]["source"]["file"] == str(path.resolve())
    assert t["repo"]["root"] == str(repo.resolve()) and t["settings"]["check"] == "grep -q brief result.txt"
    assert t["prompts"]["b"].endswith("BRIEF: treat my belief as a hypothesis.\n") and t["fidelity"] is None
    assert [c["role"] for c in agents()] == ["worker", "worker"]
    assert not (Path(os.environ["BRIEFBENCH_HOME"]) / "repos.json").exists()    # task settings stay in the file


@pytest.mark.parametrize("check,kind", [("true", "both_passed"), ("false", "both_failed")])
def test_check_scoring_names_a_tie_by_what_the_check_found(agents, repo, tip, tmp_path, check, kind):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, check=check))], "", cwd=tmp_path)
    assert code == 0, err
    [t] = entries()
    assert t["decision"] == {"by": "check", "winner": "tie", "sides": t["decision"]["sides"], "pick": None,
                             "guess": None, "tie": None, "check_tie": kind}


def test_a_task_file_can_pin_its_commit(agents, repo, tip, tmp_path):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    first = cli.runner.head(repo)
    (repo / "later.txt").write_text("x\n")
    cli.runner.git(repo, "add", "-A")
    cli.runner.git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "later")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, commit=first[:12]))], "", cwd=tmp_path)
    assert code == 0, err
    assert entries()[0]["repo"]["commit"] == first
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, commit="0" * 40))], "", cwd=tmp_path)
    assert code == 3 and "has no commit" in err


@pytest.mark.parametrize("a", ["original", "clarified"])
def test_a_task_file_does_not_run_a_skill_treatment_yet(agents, repo, tmp_path, a):
    assert bench(["init", "exp", "--a", a, "--b", f"skill:{SKILL}", "--worker", "codex", "--worker-model",
                  "", "--rewriter", "codex", "--rewriter-model", "", "--judge", "none", "--cap", "50", "--rule",
                  "fixed:10", "--net-min", "0.05", "--scoring", "check", "-y"], cwd=repo)[0] == 0
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 2 and "skill treatment" in err and entries() == [] and agents() == []


def test_a_task_file_needs_check_scoring(agents, repo, tip, tmp_path):
    """Under pick scoring, a tie would wait for a pick nobody is there to give, after two agent runs."""
    init(repo, f"snippet:{tip}")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, check="true"))], "", cwd=tmp_path)
    assert code == 2 and "--scoring check" in err and entries() == [] and agents() == []


def test_each_arm_gets_its_own_clone_outside_the_data_folder(agents, repo, tip, tmp_path):
    """No git link, sibling folder or parent leads from an arm to the other arm, the task's folder or the records."""
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    meta = json.loads(Path(t["output"], "meta.json").read_text())
    home = Path(os.environ["BRIEFBENCH_HOME"])
    clones = {side: Path(path) for side, path in meta["clones"].items()}
    assert clones["a"].parent != clones["b"].parent and all(home not in p.parents for p in clones.values())
    for path in clones.values():
        assert (path / ".git").is_dir()                     # a clone, not a worktree pointing back
        assert cli.runner.git(path, "remote").strip() == ""
        assert cli.runner.git(path, "worktree", "list").count("\n") == 1
    workers = [c for c in agents() if c["role"] == "worker"]
    assert {Path(c["cwd"]).resolve() for c in workers} == {p.resolve() for p in clones.values()}
    assert all(t["arms"][s]["looked_outside"] is False for s in "ab")
    assert bench(["clean"])[0] == 0 and not any(p.exists() for p in clones.values())


def test_an_arm_that_names_the_data_folder_is_flagged(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "peek")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["arms"]["a"]["looked_outside"] and t["arms"]["b"]["looked_outside"]
    from briefbench import experiment, score
    exp = experiment.load("exp", os.environ)
    assert score.summary(exp, entries())["looked_outside"] == 1
    assert "names the data folder" in score.report(exp, entries())


def test_an_arm_stopped_by_the_service_fails_the_trial_instead_of_losing_it(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "limit")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 4 and "measures the service" in err
    [f] = entries()
    assert f["kind"] == "failed" and f["stage"] == "run" and "usage limit" in f["error"]


def test_the_worker_never_gets_the_hidden_check(agents, repo, tip, tmp_path):
    """A Claude Code worker may run exactly the check command in pick-scored experiments; never the hidden one."""
    assert bench(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "claude-code",
                  "--worker-model", "", "--judge", "none", "--cap", "50", "--rule", "fixed:10", "--net-min", "0.05",
                  "--scoring", "check", "-y"], cwd=repo)[0] == 0
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    workers = [c for c in agents() if c["role"] == "worker"]
    assert workers and not any("grep -q brief" in arg for c in workers for arg in c["argv"])


@pytest.mark.parametrize("change,words", [
    ({"format": 2}, "not a task file"),
    ({"format": True}, "not a task file"),
    ({"prompt": ""}, "no prompt"),
    ({"type": "poem"}, "type 'poem'"),
    ({"protected": "tests/"}, "a bad protected"),
    ({"repo": "nowhere"}, "isn't there"),
])
def test_a_bad_task_file_is_refused_before_anything_runs(agents, repo, tip, tmp_path, change, words):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    path = task_file(tmp_path, repo)
    path.write_text(json.dumps(json.loads(path.read_text()) | change))
    code, err = bench(["ab", "--task", str(path)], "", cwd=tmp_path)
    assert code == 2 and words in err and entries() == [] and agents() == []


def test_a_task_file_and_a_prompt_are_one_or_the_other(agents, repo, tip, tmp_path):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "a prompt", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 2 and "not both" in err


def test_a_check_scored_trial_needs_a_check(agents, repo, tip):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    typed = "\n".join(["", "", "", "code", "", "", "goal", "none"]) + "\n"
    code, err = bench(["ab", "Make result.txt say what it is"], typed, cwd=repo)
    assert code == 2 and "needs a check" in err and entries() == [] and agents() == []


def test_task_file_protected_paths_are_a_list(agents, repo, tip, tmp_path, monkeypatch):
    """Paths come as a list, so a comma in a path is just a comma; a protected change fails that arm's check."""
    (repo / "tests" / "a,b.py").write_text("x = 1\n")
    cli.runner.git(repo, "add", "-A")
    cli.runner.git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "comma")
    monkeypatch.setenv("FAKE_WORKER", "edit-tests")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    path = task_file(tmp_path, repo, check="true", protected=["tests/test_x.py", "tests/a,b.py"])
    assert bench(["ab", "--task", str(path)], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["settings"]["protected"] == ["tests/test_x.py", "tests/a,b.py"]
    assert t["arms"]["a"]["protected_changed"] and t["decision"]["check_tie"] == "both_failed"

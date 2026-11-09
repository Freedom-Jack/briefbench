"""Unattended trials: init --scoring check, the fixed rule's declared threshold, and ab --task, through fake agent
CLIs (tests/fake_agent.py). The fake worker writes "brief" into result.txt when its prompt holds BRIEF."""
import hashlib
import io
import json
import os
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.log import read_entries

SKILL = Path(__file__).resolve().parents[1] / "skills" / "brief"


def peek(monkeypatch, tmp_path, command):
    """A peeking fake worker prints `command` as if it had run it. The command comes from a file: a variable naming a
    denied folder never reaches the worker's environment."""
    (tmp_path / "peek.txt").write_text(command)
    monkeypatch.setenv("FAKE_PEEK_FILE", str(tmp_path / "peek.txt"))


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
    return bench(["init", "exp", "--a", "original", "--b", b, "--worker", "claude-code", "--worker-model", "",
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
    assert code == 2 and "declare --net-min" in err and "A public test declares 0" in err
    code, err = init(repo, f"snippet:{tip}", "--scoring", "check", "--rule", "fixed:30", "--net-min", "0")
    assert code == 0, err
    assert frozen()["rule"] == {"kind": "fixed", "trials": 30, "alpha": 0.05, "net_min": 0.0}


def test_a_threshold_belongs_to_a_fixed_rule(agents, repo, tip):
    assert init(repo, f"snippet:{tip}", "--net-min", "0.05")[0] == 2
    assert init(repo, f"snippet:{tip}", "--rule", "fixed:30", "--alpha", "0")[0] == 2
    code, err = init(repo, f"snippet:{tip}", "--rule", "fixed:30", "--net-min", "0.05", "--alpha", "0.025",
                     "--scoring", "check")
    assert code == 0, err
    exp = frozen()
    assert exp["rule"] == {"kind": "fixed", "trials": 30, "alpha": 0.025, "net_min": 0.05}
    assert exp["scoring"] == "check" and "Scored by the check alone" in err


CHECK = ("--rule", "fixed:10", "--net-min", "0", "--scoring", "check")


@pytest.mark.parametrize("extra,words", [
    (("--strata", "belief-wrong,belief-right"), "with --scoring check"),          # pick scoring
    (CHECK + ("--strata", "belief-wrong"), "two kinds of task"),
    (CHECK + ("--strata", "same,same"), "two kinds of task"),
    (CHECK + ("--margin", "0.1"), "two kinds of task"),
    (CHECK + ("--strata", "a,b", "--margin", "0"), "above 0"),
])
def test_kinds_of_task_are_two_names_with_check_scoring(agents, repo, tip, extra, words):
    code, err = init(repo, f"snippet:{tip}", *extra)
    assert code == 2 and words in err and not (Path(os.environ["BRIEFBENCH_HOME"]) / "experiments").exists()


def test_kinds_of_task_are_frozen_and_each_trial_records_its_kind(agents, repo, tip, tmp_path):
    code, err = init(repo, f"snippet:{tip}", *CHECK, "--strata", "belief-wrong,belief-right")
    assert code == 0, err
    assert frozen()["strata"] == {"help": "belief-wrong", "harm": "belief-right", "margin": 0.10}
    assert "belief-wrong, where B should help, is tested" in err and "no loss over 10 points" in err
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, stratum="belief-wrong"))], "", cwd=tmp_path)
    assert code == 0, err
    [t] = entries()
    assert t["task"]["source"]["stratum"] == "belief-wrong"


@pytest.mark.parametrize("fields", [{}, {"stratum": "elsewhere"}])
def test_a_task_of_another_kind_is_refused_before_anything_runs(agents, repo, tip, tmp_path, fields):
    init(repo, f"snippet:{tip}", *CHECK, "--strata", "belief-wrong,belief-right", "--margin", "0.05")
    assert frozen()["strata"]["margin"] == 0.05
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, **fields))], "", cwd=tmp_path)
    assert code == 2 and "tests only belief-wrong and belief-right" in err and entries() == [] and agents() == []


def test_an_experiment_without_kinds_records_none(agents, repo, tip, tmp_path):
    init(repo, f"snippet:{tip}", *CHECK)
    assert frozen()["strata"] is None
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    assert entries()[0]["task"]["source"]["stratum"] is None


def listed(tmp_path, repo, count=2, **fields):
    """A list of `count` task files from one generator, as init --tasks reads it."""
    folder = tmp_path / "keys"
    folder.mkdir(exist_ok=True)
    for n in range(count):
        (folder / f"t{n}.json").write_text(json.dumps({
            "format": 1, "id": f"t-{n}", "set": "demo/1", "repo": str(repo), "prompt": "Make result.txt say what it is",
            "type": "analysis", "goal": "Say what it is", "check": "grep -q brief result.txt",
            "generator_sha256": "g" * 64, "checker_sha256": "c" * 64, **fields}))
    (folder / "tasks.txt").write_text("".join(f"t{n}.json\n" for n in range(count)))
    return folder / "tasks.txt"


TEST = ("--stage", "test", "--plan-commit", "abc1234", "--seed-source", "drand quicknet round 1")


@pytest.mark.parametrize("extra,words", [
    (("--stage", "test"), "--plan-commit"),
    (("--stage", "replication", "--plan-commit", "abc1234"), "--replicates"),
    (("--replicates", "first-test"), "--replicates"),
    (("--plan-commit", "not-a-commit"), "hexadecimal"),
    (("--plan-url", "https://example.org/plan"), "--plan-url goes with --plan-commit"),
    (("--stage", "test", "--plan-commit", "abc1234"), "--tasks and --seed-source"),
])
def test_a_test_needs_its_plan_and_its_frozen_tasks(agents, repo, tip, extra, words):
    code, err = init(repo, f"snippet:{tip}", *CHECK, *extra)
    assert code == 2 and words in err and not (Path(os.environ["BRIEFBENCH_HOME"]) / "experiments").exists()


def test_the_stage_the_plan_and_the_materials_are_frozen(agents, repo, tip, tmp_path):
    tasks_list = listed(tmp_path, repo)
    code, err = init(tmp_path, f"snippet:{tip}", *CHECK, *TEST, "--plan-url", "https://example.org/plan", "--tasks",
                     "keys/tasks.txt")                            # a relative list, read from init's folder
    assert code == 0, err
    exp = frozen()
    assert (exp["stage"], exp["replicates"]) == ("test", None)
    assert exp["plan"] == {"commit": "abc1234", "url": "https://example.org/plan"}
    hashes = [hashlib.sha256((tasks_list.parent / f"t{n}.json").read_bytes()).hexdigest() for n in range(2)]
    assert exp["materials"] == {"set": "demo/1", "generator_sha256": "g" * 64, "checker_sha256": "c" * 64,
                                "tasks_sha256": hashlib.sha256("\n".join(hashes).encode()).hexdigest(),
                                "tasks": hashes, "seed_source": "drand quicknet round 1"}
    assert "Stage: a first test, plan abc1234. Materials: 2 task files of demo/1, frozen by hash." in err


def test_ab_refuses_a_task_outside_the_frozen_list(agents, repo, tip, tmp_path):
    tasks_list = listed(tmp_path, repo)
    init(repo, f"snippet:{tip}", *CHECK, *TEST, "--tasks", str(tasks_list))
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, generator_sha256="g" * 64))], "", cwd=tmp_path)
    assert code == 2 and "isn't in the task list frozen with experiment exp" in err
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, generator_sha256="h" * 64))], "", cwd=tmp_path)
    assert code == 2 and "another generator" in err and entries() == [] and agents() == []
    code, err = bench(["ab", "--task", str(tasks_list.parent / "t1.json")], "", cwd=tmp_path)
    assert code == 0, err
    from briefbench import experiment, score
    exp = experiment.load("exp", os.environ)
    assert score.report(exp, entries()).startswith("Experiment exp (a first test, plan abc1234): A is original")
    scope = score.summary(exp, entries())["scope"]
    assert scope["stage"] == "test" and scope["materials_frozen"]["task_files"] == 2
    assert "tasks" not in scope["materials_frozen"]


@pytest.mark.parametrize("change,words", [({"generator_sha256": "h" * 64}, "one generator"),
                                          ({"set": "other/1"}, "one set"),
                                          ({"stratum": "elsewhere"}, "no kind the experiment tests")])
def test_a_task_list_comes_from_one_generator_and_the_frozen_kinds(agents, repo, tip, tmp_path, change, words):
    tasks_list = listed(tmp_path, repo, stratum="belief-wrong")
    first = tasks_list.parent / "t0.json"
    first.write_text(json.dumps(json.loads(first.read_text()) | change))
    code, err = init(repo, f"snippet:{tip}", *CHECK, *TEST, "--strata", "belief-wrong,belief-right", "--tasks",
                     str(tasks_list))
    assert code == 2 and words in err


def test_a_halfway_look_belongs_to_a_fixed_rule_and_comes_before_its_end(agents, repo, tip):
    assert init(repo, f"snippet:{tip}", "--futility-at", "5")[0] == 2                     # the two-step rule
    assert init(repo, f"snippet:{tip}", *CHECK, "--futility-at", "10")[0] == 2           # N is 10
    code, err = init(repo, f"snippet:{tip}", *CHECK, "--futility-at", "5")
    assert code == 0, err
    assert frozen()["rule"] == {"kind": "fixed", "trials": 10, "alpha": 0.05, "net_min": 0.0, "futility_at": 5}
    assert "A halfway look after 5 trials stops the test unless B is ahead." in err


def test_an_experiment_records_pick_scoring_by_default(agents, repo, tip):
    assert init(repo, f"snippet:{tip}")[0] == 0
    assert frozen()["scoring"] == "pick"
    assert (frozen()["stage"], frozen()["plan"], frozen()["materials"]) == ("development", None, None)


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
    assert bench(["init", "exp", "--a", a, "--b", f"skill:{SKILL}", "--worker", "claude-code", "--worker-model",
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
    peek(monkeypatch, tmp_path, f"ls {os.environ['BRIEFBENCH_HOME']}/keys")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["arms"]["a"]["looked_outside"] and t["arms"]["b"]["looked_outside"]
    from briefbench import experiment, score
    exp = experiment.load("exp", os.environ)
    assert score.summary(exp, entries())["looked_outside"] == 1
    assert "names a folder it must not read" in score.report(exp, entries())
    assert "If it confirms the look, that arm counts as failing its check" in score.report(exp, entries())


def test_a_path_that_only_starts_like_the_data_folder_is_not_flagged(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "peek")
    peek(monkeypatch, tmp_path, f"ls {os.environ['BRIEFBENCH_HOME']}-elsewhere/x")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["arms"]["a"]["looked_outside"] is False and t["arms"]["b"]["looked_outside"] is False
    meta = json.loads(Path(t["output"], "meta.json").read_text())
    assert all(not path.startswith(os.environ["BRIEFBENCH_HOME"]) for path in meta["clones"].values())


def test_an_arm_stopped_by_the_service_fails_the_trial_instead_of_losing_it(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "limit")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 4 and "measures the service" in err
    [f] = entries()
    assert f["kind"] == "failed" and f["stage"] == "run" and "reported an error" in f["error"]


def test_the_worker_never_gets_the_hidden_check_and_works_sandboxed(agents, repo, tip, tmp_path):
    """Scored by the check alone, a Claude Code worker gets no check command, may run any shell command inside
    its sandbox, and is barred from the data folder and from the other arm's folder."""
    assert bench(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "claude-code",
                  "--worker-model", "", "--judge", "none", "--cap", "50", "--rule", "fixed:10", "--net-min", "0.05",
                  "--scoring", "check", "-y"], cwd=repo)[0] == 0
    assert "--settings" in json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json")
                                      .read_text())["worker"]["argv"]                    # frozen with the experiment
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    clones = json.loads(Path(t["output"], "meta.json").read_text())["clones"]
    workers = [c for c in agents() if c["role"] == "worker"]
    assert len(workers) == 2
    for call in workers:
        argv = call["argv"]
        assert not any("grep -q brief" in arg or arg.startswith("--allowedTools") for arg in argv)
        assert argv[argv.index("--output-format") + 1] == "stream-json"
        settings = json.loads(argv[argv.index("--settings") + 1])
        assert settings["sandbox"]["enabled"] and settings["sandbox"]["failIfUnavailable"]
        mine = next(side for side, path in clones.items() if Path(path).resolve() == Path(call["cwd"]).resolve())
        theirs = str(Path(clones["b" if mine == "a" else "a"]).parent)
        denied = settings["sandbox"]["filesystem"]["denyRead"]
        assert denied[:2] == [os.environ["BRIEFBENCH_HOME"], theirs]
        assert settings["permissions"]["deny"] == [f"Read(/{p}/**)" for p in denied]
        assert settings["permissions"]["allow"] == ["Bash"] and not settings["sandbox"]["allowUnsandboxedCommands"]


def test_each_arm_has_a_temporary_folder_of_its_own(agents, repo, tip, tmp_path):
    """The two arms of a task-file trial share no temporary folder: each gets its own, through TMPDIR and the CLI's
    own setting, and can't read the other's. clean removes them with the clones."""
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    meta = json.loads(Path(t["output"], "meta.json").read_text())
    temps, clones = meta["temps"], meta["clones"]
    assert temps["a"] != temps["b"] and all(Path(p).is_dir() and Path(p).name.startswith("bb-") for p in temps.values())
    for call in [c for c in agents() if c["role"] == "worker"]:
        mine = next(side for side, path in clones.items() if Path(path).resolve() == Path(call["cwd"]).resolve())
        theirs = "b" if mine == "a" else "a"
        assert call["env"]["TMPDIR"] == temps[mine] == call["env"]["CLAUDE_CODE_TMPDIR"]
        argv = call["argv"]
        assert temps[theirs] in json.loads(argv[argv.index("--settings") + 1])["sandbox"]["filesystem"]["denyRead"]
    assert bench(["clean"])[0] == 0
    assert not any(Path(p).exists() for p in [*temps.values(), *clones.values()])


def test_the_worker_can_reach_neither_the_bench_source_nor_other_sessions_files(agents, repo, tip, tmp_path,
                                                                               monkeypatch):
    """The bench's own source, whose generators say how materials hide their answers, and the places where agent CLIs
    keep other sessions' transcripts are denied. Nothing in the worker's environment, PATH included, names them."""
    projects = Path(os.environ["HOME"], ".claude", "projects")
    projects.mkdir(parents=True)
    root = Path(cli.__file__).resolve().parents[2]
    monkeypatch.setenv("PATH", f"{root / '.venv' / 'bin'}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("VIRTUAL_ENV", str(root / ".venv"))
    monkeypatch.setenv("WHERE_RECORDS_ARE", os.environ["BRIEFBENCH_HOME"])
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    for call in [c for c in agents() if c["role"] == "worker"]:
        argv = call["argv"]
        denied = json.loads(argv[argv.index("--settings") + 1])["sandbox"]["filesystem"]["denyRead"]
        assert str(root) in denied and str(projects) in denied
        assert not any(str(root) in value for value in call["env"].values())
        assert not {"VIRTUAL_ENV", "BRIEFBENCH_HOME", "WHERE_RECORDS_ARE"} & set(call["env"])


def test_a_pick_scored_worker_keeps_its_one_allowed_command(agents, repo, tip):
    """Outside check scoring nothing changes: a Claude Code worker may run exactly your check, and no sandbox."""
    assert bench(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "claude-code",
                  "--worker-model", "", "--judge", "none", "--cap", "50", "-y"], cwd=repo)[0] == 0
    typed = "\n".join(["", "", "", "code", "", "", "goal", "grep -q brief result.txt"]) + "\n" + "n\n"
    assert bench(["ab", "Make result.txt say what it is"], typed, cwd=repo)[0] == 0
    workers = [c for c in agents() if c["role"] == "worker"]
    assert all("--allowedTools=Bash(grep -q brief result.txt:*)" in c["argv"] and "--settings" not in c["argv"]
               for c in workers)


@pytest.mark.parametrize("change,words", [
    ({"format": 2}, "not a task file"),
    ({"format": True}, "not a task file"),
    ({"prompt": ""}, "no prompt"),
    ({"type": "poem"}, "type 'poem'"),
    ({"protected": "tests/"}, "a bad protected"),
    ({"stratum": 1}, "a bad stratum"),
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


def test_a_worker_that_cant_be_confined_doesnt_run_check_scored_experiments(agents, repo, tip):
    code, err = bench(["init", "exp", "--a", "original", "--b", f"snippet:{tip}", "--worker", "codex", "--worker-model",
                       "", "--judge", "none", "--cap", "50", "--rule", "fixed:10", "--net-min", "0.05", "--scoring",
                       "check", "-y"], cwd=repo)
    assert code == 2 and "can't yet be kept from reading other folders" in err


def test_check_scoring_runs_task_files_only(agents, repo, tip):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "Make result.txt say what it is"], "", cwd=repo)
    assert code == 2 and "--task" in err and entries() == [] and agents() == []


def test_each_arm_is_kept_from_the_keys_and_from_leftover_clones(agents, repo, tip, tmp_path):
    """The deny list covers the data folder, the folder of task files and keys, the other arm and any earlier
    trial's leftover clone; never a folder the arm itself works in. The arm gets no BRIEFBENCH_HOME, and its clone
    keeps no reflog naming the task's folder."""
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    keys = tmp_path / "keys" / "t-001"
    keys.mkdir(parents=True)
    path = task_file(keys, repo)
    runs = Path(os.environ["HOME"], ".cache", "briefbench-runs")
    (runs / "briefbench-leftover" / "work").mkdir(parents=True)
    assert bench(["ab", "--task", str(path)], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    clones = json.loads(Path(t["output"], "meta.json").read_text())["clones"]
    for call in [c for c in agents() if c["role"] == "worker"]:
        argv = call["argv"]
        denied = json.loads(argv[argv.index("--settings") + 1])["sandbox"]["filesystem"]["denyRead"]
        mine = Path(call["cwd"]).resolve().parent
        assert os.environ["BRIEFBENCH_HOME"] in denied and str(tmp_path / "keys") in denied
        assert str(runs / "briefbench-leftover") in denied
        assert not any(mine == Path(d).resolve() or Path(d).resolve() in mine.parents for d in denied)
        assert call["data_home"] is False
    for clone in clones.values():
        logs = cli.runner.git(Path(clone), "reflog", "--all")
        assert str(repo) not in logs and not (Path(clone) / ".git" / "logs").exists()


def test_a_look_spelt_from_the_home_folder_is_flagged(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("BRIEFBENCH_HOME", os.path.join(os.environ["HOME"], ".bbdata"))
    monkeypatch.setenv("FAKE_WORKER", "peek")
    peek(monkeypatch, tmp_path, "cat ~/.bbdata/keys/x")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["arms"]["a"]["looked_outside"] and t["arms"]["b"]["looked_outside"]


def test_a_data_folder_that_clashes_with_the_runs_folder_is_refused(agents, repo, tip, tmp_path, monkeypatch):
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    clash = os.path.join(os.environ["HOME"], ".cache", "briefbench")
    import shutil
    shutil.copytree(os.environ["BRIEFBENCH_HOME"], clash)
    monkeypatch.setenv("BRIEFBENCH_HOME", clash)
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 3 and "start alike" in err


def test_a_run_cut_off_before_its_result_fails_the_trial(agents, repo, tip, tmp_path, monkeypatch):
    """No result line means the service or the sandbox failed: the trial is logged as failed, to be rerun."""
    monkeypatch.setenv("FAKE_WORKER", "cutoff")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 4 and "no JSON result" in err
    assert entries()[0]["kind"] == "failed"


def test_an_arm_stopped_at_the_timeout_is_an_outcome(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "sleep")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check", "--timeout", "0.02")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo, check="true"))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["kind"] == "trial" and t["arms"]["a"]["timed_out"] and t["arms"]["a"]["error"]

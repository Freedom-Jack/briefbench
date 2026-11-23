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
from conftest import KEY

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


@pytest.mark.parametrize("mode,turns", [("none", 1), ("one", 2), ("two", 3)])
def test_session_interview_reuses_context_and_returns_the_brief(agents, repo, tmp_path, monkeypatch, mode, turns):
    monkeypatch.setenv("FAKE_ASKER", mode)
    code, err = init(repo, f"skill:{SKILL}", *CHECK, "--rewriter", "claude-code", "--rewriter-model", "",
                     "--interview", "session", "--pin-versions")
    assert code == 0, err
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=["For the team."]))])
    assert code == 0, err
    [row] = entries()
    calls = [c for c in agents() if c["role"] == "asker"]
    assert len(calls) == turns and len({c["pid"] for c in calls}) == 1
    assert "<skill>" in calls[0]["prompt"] and all("<skill>" not in c["prompt"] for c in calls[1:])
    assert all("Say what it is" not in c["prompt"] and "grep" not in c["prompt"] for c in calls)
    assert not any(c["role"] == "rewriter" for c in agents())
    headless = [c for c in row["task"]["headless"] if c["skill"]]
    assert sum(c["cost_usd"] for c in headless) == pytest.approx(turns * .01)
    assert sum(c["tokens"] for c in headless) == sum(15 + n * 10 for n in range(turns))
    assert row["prompts"]["b"] == "BRIEF: do it.\n"
    assert row["arms"]["b"]["check"]["passed"] and row["arms"]["a"]["brief"] is None


def test_session_turn_guardrail_is_an_incomplete_comparison(agents, repo, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_ASKER", "endless")
    init(repo, f"skill:{SKILL}", *CHECK, "--rewriter", "claude-code", "--rewriter-model", "",
         "--interview", "session")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))])
    assert code == 4 and "without a finished brief" in err
    [row] = entries()
    assert row["kind"] == "failed" and row["task"]["interview"][f"skill:{SKILL}"]["capped"]
    assert not any(c["role"] in ("worker", "rewriter") for c in agents())


def test_pinned_versions_refuse_drift_before_model_calls(agents, repo, tmp_path, tip, monkeypatch):
    init(repo, f"snippet:{tip}", *CHECK, "--pin-versions")
    monkeypatch.setenv("FAKE_VERSION", "2.0")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))])
    assert code == 3 and "CLI version changed" in err and not agents() and not entries()


def test_interrupted_work_records_unknown_usage_for_the_guardrail(agents, repo, tmp_path, tip, monkeypatch):
    init(repo, f"snippet:{tip}", *CHECK)
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr(cli, "_run_arms", interrupted)
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))])
    assert code == 130 and "cancelled" in err
    [row] = entries()
    assert row["kind"] == "failed" and row["usage_incomplete"]


def test_session_clarified_uses_the_answers_without_charging_it_for_the_final_brief(agents, repo, tmp_path):
    init(repo, f"skill:{SKILL}", *CHECK, "--a", "clarified", "--rewriter", "claude-code", "--rewriter-model", "",
         "--interview", "session")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=["For the team."]))])
    assert code == 0, err
    [row] = entries()
    assert "For the team." in row["prompts"]["a"] and "BRIEF" not in row["prompts"]["a"]
    calls = [c for c in row["task"]["headless"] if c["skill"]]
    assert [c["phase"] for c in calls] == ["questions", "brief"]
    assert row["arms"]["a"]["brief"]["tokens"] == calls[0]["tokens"]
    assert row["arms"]["b"]["brief"]["tokens"] == sum(c["tokens"] for c in calls)


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
    bench = exp["bench"]                                     # the bench's own commit, from its source checkout
    assert set(bench) == {"commit", "dirty"} and len(bench["commit"]) == 40 and isinstance(bench["dirty"], bool)


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


FACTS = ["The report goes to the board on Monday.", "Only customers who signed up in 2026 count."]


def stand_in(repo, a="original", b=None, *extra):
    """An experiment scored by the check alone with a skill treatment, so the stand-in requester answers."""
    return bench(["init", "exp", "--a", a, "--b", b or f"skill:{SKILL}", "--worker", "claude-code", "--worker-model",
                  "", "--rewriter", "claude-code", "--rewriter-model", "", "--judge", "none", "--cap", "50", "-y",
                  *CHECK, *extra], cwd=repo)


def test_a_skill_scored_by_the_check_freezes_the_stand_in_and_confined_headless_calls(agents, repo):
    from briefbench import experiment, treatments
    code, err = stand_in(repo)
    assert code == 0, err
    exp = frozen()
    assert exp["render"] == experiment.RENDER_STAND_IN and exp["templates"]["answerer"] == treatments.answers_sha256()
    assert exp["answerer"]["agent"] == "claude-code" and "--tools" in exp["answerer"]["argv"]
    assert exp["answerer"]["argv"][exp["answerer"]["argv"].index("--tools") + 1] == ""      # no tools at all
    for role in ("asker", "rewriter"):                    # kept out of the places an arm may not read
        argv = exp[role]["argv"]
        assert "stream-json" in argv and '{"permissions": {"deny": {deny_rules}}}' in argv
    assert "stand-in requester, from each task file's facts" in err and "Stand-in requester" in err
    code, err = bench(["init", "exp2", "--a", "original", "--b", f"skill:{SKILL}", "--worker", "claude-code",
                       "--worker-model", "", "--rewriter", "codex", "--rewriter-model", "", "--judge", "none", "--cap",
                       "50", "-y", *CHECK], cwd=repo)
    assert code == 2 and "can't yet be kept from reading other folders" in err


def test_the_stand_in_answers_from_the_facts_and_the_brief_gets_them_word_for_word(agents, repo, tmp_path):
    stand_in(repo)
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)
    assert code == 0, err
    [t] = entries()
    assert t["task"]["answered_by"] == "stand-in"
    assert t["task"]["questions"] == [{"skill": f"skill:{SKILL}", "q": "What is the result for?", "a": FACTS[0],
                                       "turn": 1, "facts": [1]}]
    assert t["task"]["interview"] == {f"skill:{SKILL}": {"turns": 1, "capped": False}}
    out = Path(t["output"])
    asked = (out / "answers.request.md").read_text()
    assert all(f in asked for f in FACTS) and "What is the result for?" in asked
    assert "Say what it is" not in asked and "grep" not in asked              # never the goal or the check
    assert f"Answer: {FACTS[0]}" in (out / "rewrite-b.request.md").read_text()
    assert t["prompts"]["a"] == "Make result.txt say what it is" and t["prompts"]["b"].startswith("BRIEF:")
    assert all("Say what it is" not in p and "grep" not in p for p in t["prompts"].values())
    steps = {c["step"]: c for c in t["task"]["headless"]}
    assert steps["answers"]["skill"] is None                                  # the stand-in is not the arm's cost
    assert t["arms"]["b"]["brief"]["tokens"] == sum(steps[s]["tokens"] for s in ("questions-1", "questions-1.2",
                                                                               "rewrite-b"))
    assert "answers.2" not in steps                  # the second turn asked nothing, so the stand-in had nothing to answer
    assert t["fidelity"] == {"b": {"added": None, "dropped": None, "changed": None}}   # waits for your review
    assert "waits for your fidelity review" in err
    meta, calls = json.loads((out / "meta.json").read_text()), agents()
    rules = lambda c: set(json.loads(c["argv"][c["argv"].index("--settings") + 1])["permissions"]["deny"])
    arm_a = next(c for c in calls if c["role"] == "worker" and c["cwd"] == meta["clones"]["a"])
    for role in ("asker", "rewriter"):           # confined as arm A, in its clone, and kept out of arm A's temp folder
        call = next(c for c in calls if c["role"] == role)
        assert rules(call) == rules(arm_a) | {f"Read(/{meta['temps']['a']}/**)"} and not call["data_home"]
        assert call["cwd"] == meta["clones"]["a"] and call["env"]["TMPDIR"] == meta["temps"]["h"]
    assert f"Read(/{meta['temps']['h']}/**)" in rules(arm_a)          # arms can't read the headless calls' temp
    assert next(c for c in calls if c["role"] == "answerer")["cwd"] not in meta["clones"].values()


def test_clarified_gets_the_stand_ins_answers_word_for_word(agents, repo, tmp_path):
    stand_in(repo, "clarified")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert f"Q: What is the result for?\nA: {FACTS[0]}" in t["prompts"]["a"]
    assert t["arms"]["a"]["brief"]["tokens"] == sum(c["tokens"] for c in t["task"]["headless"]
                                                    if c["step"] in ("questions-1", "questions-1.2"))


def test_without_facts_every_question_is_skipped_and_the_stand_in_is_not_called(agents, repo, tmp_path):
    stand_in(repo)
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["task"]["questions"][0] | {"skill": None} == {"skill": None, "q": "What is the result for?", "a": "",
                                                           "turn": 1, "facts": []}
    assert "answerer" not in {c["role"] for c in agents()}
    assert "Answer: (skipped)" in (Path(t["output"]) / "rewrite-b.request.md").read_text()


def test_the_stand_in_can_only_choose_facts_by_number(agents, repo, tmp_path, monkeypatch):
    stand_in(repo)
    monkeypatch.setenv("FAKE_ANSWERER", "range")             # 99 and 0 are outside the list, and true isn't a number
    assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    assert entries()[-1]["task"]["questions"][0]["facts"] == [1]
    for mode in ("bad", "short"):                            # not the JSON asked for, or an answer missing
        monkeypatch.setenv("FAKE_ANSWERER", mode)
        code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)
        assert code == 4 and "stand-in requester didn't answer" in err
        assert entries()[-1]["kind"] == "failed" and entries()[-1]["stage"] == "questions"


def test_a_later_turn_of_the_interview_is_confined_and_scanned_too(agents, repo, tmp_path, monkeypatch):
    stand_in(repo)
    monkeypatch.setenv("FAKE_ASKER", "peek-later")
    peek(monkeypatch, tmp_path, f"ls {os.environ['BRIEFBENCH_HOME']}/keys")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    flags = {c["step"]: c["looked_outside"] for c in t["task"]["headless"] if "looked_outside" in c}
    assert flags["questions-1.2"] and not flags["questions-1"]
    assert t["arms"]["b"]["looked_outside"] and not t["arms"]["a"]["looked_outside"]


def test_the_stand_in_answers_every_turn_outside_the_arms_cost(agents, repo, tmp_path, monkeypatch):
    stand_in(repo)
    monkeypatch.setenv("FAKE_ASKER", "two")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert [(x["q"], x["a"], x["turn"]) for x in t["task"]["questions"]] == [
        ("What is the result for?", FACTS[0], 1), ("Who reads it?", FACTS[0], 2)]
    steps = {c["step"]: c for c in t["task"]["headless"]}
    assert steps["answers"]["skill"] is None and steps["answers.2"]["skill"] is None
    assert "Who reads it?" in (Path(t["output"]) / "answers.2.request.md").read_text()
    assert t["arms"]["b"]["brief"]["tokens"] == sum(steps[s]["tokens"] for s in ("questions-1", "questions-1.2",
                                                                               "questions-1.3", "rewrite-b"))


def test_a_headless_call_that_names_a_denied_place_flags_the_arms_it_reached(agents, repo, tmp_path, monkeypatch):
    stand_in(repo)
    monkeypatch.setenv("FAKE_ASKER", "peek")
    peek(monkeypatch, tmp_path, f"ls {os.environ['BRIEFBENCH_HOME']}/keys")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["arms"]["b"]["looked_outside"] and not t["arms"]["a"]["looked_outside"]
    assert next(c for c in t["task"]["headless"] if c["step"] == "questions-1")["looked_outside"]


def test_the_clis_own_notice_of_a_saved_output_is_not_a_look_but_opening_the_file_is(agents, repo, tmp_path,
                                                                                    monkeypatch):
    """Round 1's six false flags: a skill's headless call got a Grep output too large for its result, which Claude Code
    saved under ~/.claude/projects and named in its notice, and no call opened the file."""
    Path(os.environ["HOME"], ".claude", "projects").mkdir(parents=True)
    stand_in(repo)
    for mode in ("saved", "saved-read"):
        monkeypatch.setenv("FAKE_ASKER", mode)
        assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    notice, opened = entries()
    assert "/.claude/projects/" in Path(notice["output"], "questions-1.out").read_text()    # kept there as printed
    for t, flagged in ((notice, False), (opened, True)):
        assert next(c for c in t["task"]["headless"] if c["step"] == "questions-1")["looked_outside"] is flagged
        assert t["arms"]["b"]["looked_outside"] is flagged and t["arms"]["a"]["looked_outside"] is False


def test_an_older_skill_experiment_without_the_stand_in_cant_run_task_files(agents, repo, tmp_path):
    from briefbench import experiment
    stand_in(repo)
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json"
    path.write_text(json.dumps(frozen() | {"render": experiment.RENDER, "answerer": None}))
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)
    assert code == 2 and "no stand-in requester" in err and entries() == []


def test_an_experiment_that_asked_once_runs_no_more_trials_but_is_still_scored(agents, repo, tmp_path):
    """Rounds 1 and 2 asked the skill's questions once, at most three (skill-questions/1+stand-in/1): `ab` no longer
    runs such an experiment, and `score` still reads it, its review policy included."""
    stand_in(repo)
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json"
    path.write_text(json.dumps(frozen() | {"render": "skill-questions/1+stand-in/1"}))
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)
    assert code == 3 and "frozen by an older briefbench" in err and entries() == []
    out = io.StringIO()
    assert cli.run(["score", "exp", "--json"], stdout=out, stderr=io.StringIO(), cwd=tmp_path) == 0
    assert json.loads(out.getvalue())["fidelity_review"]["policy"] == {"sample": None, "max_unfaithful": 0}


def test_a_changed_stand_in_request_needs_a_new_experiment(agents, repo, tmp_path, monkeypatch):
    from briefbench import treatments
    stand_in(repo)
    monkeypatch.setattr(treatments, "ANSWER_REQUEST", treatments.ANSWER_REQUEST + "\nBe generous.")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)
    assert code == 3 and "stand-in requester's request" in err and entries() == []


def test_a_stand_in_experiment_adopts_nothing_until_its_briefs_are_reviewed(agents, repo, tmp_path):
    """The fake brief makes result.txt say brief, so B wins all 10 trials; without a single fidelity review, the rule's
    benefit is blocked."""
    from briefbench import experiment, score
    stand_in(repo)
    for _ in range(10):
        assert bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS))], "", cwd=tmp_path)[0] == 0
    verdict = score.summary(experiment.load("exp", os.environ), entries())["verdict"]
    assert verdict["state"] == "benefit" and not verdict["adopted"]
    assert "10 of the 10 briefs chosen for review have no fidelity review yet" in verdict["blocked_by"]


def test_a_task_file_with_bad_facts_is_refused(agents, repo, tmp_path):
    stand_in(repo)
    for facts in ("one fact", [""], [1]):
        code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=facts))], "", cwd=tmp_path)
        assert code == 2 and "a bad facts" in err


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


def test_a_failed_trial_gives_each_arms_error_in_the_clis_words_without_keys(agents, repo, tip, tmp_path,
                                                                             monkeypatch):
    """In round 1 a usage limit ended both arms with subtype success, and the bench said "(success)", hiding the
    message. Now the message says what the CLI said, after its HTTP status, with key values scrubbed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("FAKE_LIMIT", f"You've hit your usage limit · key {KEY} · resets 7pm (America/Toronto)")
    monkeypatch.setenv("FAKE_WORKER", "limit")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    said = ("briefbench: arms A and B both reported an error: HTTP 429: You've hit your usage limit · key [redacted] · "
            "resets 7pm (America/Toronto). With the check alone deciding, that measures the service")
    assert code == 4 and said in err and entries()[-1]["error"] == said.removeprefix("briefbench: ") + (
        ", not the prompt, so the trial is logged as failed: rerun its task once.")
    monkeypatch.setenv("FAKE_WORKER", "limit-b")                    # only B's worker reached the limit
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)
    assert code == 4 and "briefbench: arm B reported an error: HTTP 429: You've hit" in err and "arm A" not in err
    log = Path(os.environ["BRIEFBENCH_HOME"], "log.jsonl").read_text()
    assert KEY not in err + log and "(success)" not in log and [e["kind"] for e in entries()] == ["failed"] * 2


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
    [t] = entries()          # the start-up report names the arm's memory folder there, which isn't a look
    assert t["arms"]["a"]["looked_outside"] is False and t["arms"]["b"]["looked_outside"] is False


def test_a_look_at_other_sessions_transcripts_is_flagged(agents, repo, tip, tmp_path, monkeypatch):
    Path(os.environ["HOME"], ".claude", "projects").mkdir(parents=True)
    monkeypatch.setenv("FAKE_WORKER", "peek")
    peek(monkeypatch, tmp_path, "ls ~/.claude/projects")
    init(repo, f"snippet:{tip}", "--rule", "fixed:10", "--net-min", "0.05", "--scoring", "check")
    assert bench(["ab", "--task", str(task_file(tmp_path, repo))], "", cwd=tmp_path)[0] == 0
    [t] = entries()
    assert t["arms"]["a"]["looked_outside"] and t["arms"]["b"]["looked_outside"]


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


# ----------------------------------------------------------------------------- runs of one arm, for the bench

def test_only_runs_one_arm_once_and_logs_a_run_not_a_trial(agents, repo, tip, tmp_path):
    """The bench shares the plain prompt's runs among every trick, so a trick's experiment runs only its own arm."""
    assert init(repo, f"snippet:{tip}", *CHECK)[0] == 0
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo)), "--only", "b"], "", cwd=tmp_path)
    assert code == 0, err
    [r] = entries()
    assert r["kind"] == "run" and r["side"] == "b" and "decision" not in r and "judge" not in r
    assert set(r["arms"]) == set(r["prompts"]) == set(r["treatments"]) == {"b"}
    assert r["treatments"]["b"] == f"snippet:{tip}" and r["arms"]["b"]["check"]["passed"] is True
    assert r["arms"]["b"]["looked_outside"] is False and r["fidelity"] is None and r["arms"]["b"]["brief"] is None
    meta = json.loads(Path(r["output"], "meta.json").read_text())
    assert set(meta["clones"]) == {"b"} and set(meta["temps"]) == {"b", "h"}
    assert [c["role"] for c in agents()] == ["worker"] and (Path(r["output"]) / "b.prompt.md").exists()
    assert "only arm B runs" in err and "Logged as a run" in err
    summary = cli.score.summary(frozen(), entries())                 # score reads trials, never runs
    assert summary["trials"] == 0 and summary["failed"]["trials"] == 0


@pytest.mark.parametrize("extra", [("--aa",), ()])
def test_only_goes_with_a_task_file_and_not_with_a_noise_check(agents, repo, tip, tmp_path, extra):
    assert init(repo, f"snippet:{tip}", *CHECK)[0] == 0
    task = ["--task", str(task_file(tmp_path, repo))] if extra else ["Make result.txt say what it is"]
    code, err = bench(["ab", *task, "--only", "b", *extra], "", cwd=tmp_path)
    assert code == 2 and "--only runs one arm" in err and entries() == []


def test_a_run_of_the_plain_prompt_runs_arm_a(agents, repo, tip, tmp_path):
    assert init(repo, f"snippet:{tip}", *CHECK)[0] == 0
    assert bench(["ab", "--task", str(task_file(tmp_path, repo)), "--only", "a"], "", cwd=tmp_path)[0] == 0
    [r] = entries()
    assert r["side"] == "a" and r["prompts"] == {"a": "Make result.txt say what it is"}
    assert r["arms"]["a"]["check"]["passed"] is False


def test_a_run_is_kept_from_the_data_folder_the_keys_and_other_clones(agents, repo, tip, tmp_path):
    assert init(repo, f"snippet:{tip}", *CHECK)[0] == 0
    (tmp_path / "keys" / "t-001").mkdir(parents=True)            # as a generator lays them out: KEYS/<task>/task.json
    path = task_file(tmp_path, repo).rename(tmp_path / "keys" / "t-001" / "task.json")
    assert bench(["ab", "--task", str(path), "--only", "b"], "", cwd=tmp_path)[0] == 0
    [worker] = [c for c in agents() if c["role"] == "worker"]
    denied = json.loads(worker["argv"][worker["argv"].index("--settings") + 1])["sandbox"]["filesystem"]["denyRead"]
    assert denied[0] == os.environ["BRIEFBENCH_HOME"] and str(tmp_path / "keys") in denied
    assert not worker["data_home"] and "BRIEFBENCH_HOME" not in worker["env"]


def test_a_run_of_a_skill_version_interviews_through_the_stand_in(agents, repo, tmp_path):
    stand_in(repo)
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo, facts=FACTS)), "--only", "b"], "", cwd=tmp_path)
    assert code == 0, err
    [r] = entries()
    assert r["task"]["answered_by"] == "stand-in" and r["task"]["questions"][0]["a"] == FACTS[0]
    assert r["task"]["interview"] == {f"skill:{SKILL}": {"turns": 1, "capped": False}}
    assert r["prompts"]["b"].startswith("BRIEF:") and r["arms"]["b"]["brief"]["tokens"] > 0
    assert r["fidelity"] == {"b": {"added": None, "dropped": None, "changed": None}}
    meta, calls = json.loads(Path(r["output"], "meta.json").read_text()), agents()
    for role in ("asker", "rewriter"):           # the skill's calls run in the one clone, confined as its arm
        call = next(c for c in calls if c["role"] == role)
        assert call["cwd"] == meta["clones"]["b"] and call["env"]["TMPDIR"] == meta["temps"]["h"]


def test_a_failed_run_is_logged_with_its_arm_and_kept_out_of_score(agents, repo, tip, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "limit")
    assert init(repo, f"snippet:{tip}", *CHECK)[0] == 0
    code, err = bench(["ab", "--task", str(task_file(tmp_path, repo)), "--only", "b"], "", cwd=tmp_path)
    assert code == 4 and "arm B reported an error" in err
    [f] = entries()
    assert f["kind"] == "failed" and f["only"] == "b" and f["treatments"] == {"b": f"snippet:{tip}"}
    assert cli.score.summary(frozen(), entries())["failed"]["trials"] == 0


def test_from_a_git_worktree_the_main_checkout_is_denied_too(tmp_path, monkeypatch, repo):
    """The main checkout of a worktree holds the same generators, the bench's seeds and the other worktrees."""
    worktree = tmp_path / "wt"
    cli.runner.git(repo, "worktree", "add", "--detach", "--quiet", str(worktree))
    monkeypatch.setattr(cli, "_bench_source", lambda: worktree)
    assert cli._bench_places() == [worktree, repo.resolve()]
    monkeypatch.setattr(cli, "_bench_source", lambda: repo)
    assert cli._bench_places() == [repo]

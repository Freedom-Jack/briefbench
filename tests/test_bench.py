"""init, ab and clean end to end, through fake agent CLIs (tests/fake_agent.py) in a throwaway git repo."""
import io
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from briefbench import cli, judge, treatments
from briefbench.log import read_entries

SKILL = Path(__file__).resolve().parents[1] / "skills" / "brief"
PROMPT = "Make result.txt say what it is"
QUESTION = "What is the result for?"                 # the fake asker's one question


def answers(goal="Keep CI honest", check="grep -q brief result.txt", skill="It feeds the release notes",
            first=True, after="n\nn\nn\n"):
    """What you type in one `ab` run: 3 eligibility questions, the task type, setup and protected paths (first trial
    in a repo only), the goal and the check, your answer to each of the skill's questions, then what comes after the
    arms ran (by default: the check decides, then the three fidelity questions)."""
    lines = ["", "", "", "code"] + (["", "tests/"] if first else []) + [goal, check]
    lines += [skill] if skill is not None else []
    return "\n".join(lines) + "\n" + after


ANSWERS = answers()


def bench(argv, typed="", cwd=None):
    err = io.StringIO()
    return cli.run(argv, stdin=io.StringIO(typed), stderr=err, cwd=cwd), err.getvalue()


def entries():
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def init(repo, *extra, a="original", b=f"skill:{SKILL}"):
    return bench(["init", "exp", "--a", a, "--b", b, "--worker", "codex", "--worker-model", "", "--rewriter", "codex",
                  "--rewriter-model", "", "--judge", "none", "--cap", "50", "-y", *extra], cwd=repo)


def frozen():
    return json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json").read_text())


def test_init_freezes_the_experiment_once(agents, repo):
    code, err = init(repo)
    assert code == 0, err
    exp = frozen()
    assert exp["b"]["kind"] == "skill" and exp["b"]["version"] == "0.2.0" and len(exp["b"]["sha256"]) == 64
    assert exp["worker"]["agent"] == "codex" and exp["worker"]["argv"][-2:] == ["--", "{prompt}"]
    assert exp["rule"]["kind"] == "two-step" and exp["rule"]["adopt_first"] == 16 and exp["cap_percent"] == 50
    assert exp["render"] == "skill-questions/1" and "--output-schema" in exp["asker"]["argv"]
    assert "read-only" in exp["asker"]["argv"] and exp["asker"]["model"] == exp["rewriter"]["model"]
    assert "Rule: two-step" in err and "listing the skill's questions" in err
    assert init(repo)[0] == 2                                    # frozen settings are never changed
    assert stat.S_IMODE(Path(os.environ["BRIEFBENCH_HOME"]).stat().st_mode) == 0o700


def test_init_freezes_a_fixed_rule(agents, repo):
    code, err = init(repo, "--rule", "fixed:30")
    assert code == 0, err
    assert frozen()["rule"] == {"kind": "fixed", "trials": 30, "alpha": 0.05, "net_min": 0.15}
    assert "one sign test after exactly 30 trials" in err


@pytest.mark.parametrize("rule", ["fixed:5", "fixed", "sequential"])
def test_init_refuses_an_unknown_rule(agents, repo, rule):
    assert init(repo, "--rule", rule)[0] == 2


def test_original_and_snippet_need_no_rewriter(agents, repo, tmp_path):
    (tmp_path / "tip.md").write_text("Think hard.\n")
    code, err = init(repo, b=f"snippet:{tmp_path / 'tip.md'}")
    assert code == 0, err
    exp = frozen()
    assert exp["rewriter"] is None and exp["asker"] is None and exp["render"] is None


@pytest.mark.parametrize("login", ["api", "none"])
def test_init_refuses_an_agent_not_on_a_plan(agents, repo, monkeypatch, login):
    monkeypatch.setenv("FAKE_LOGIN", login)
    code, err = init(repo)
    assert code == 3 and "subscription plan" in err


def test_ab_runs_both_arms_and_the_check_decides(agents, repo, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-0123456789")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://elsewhere.invalid/v1")
    assert init(repo)[0] == 0
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["kind"] == "trial" and t["decision"]["by"] == "check" and t["decision"]["winner"] == "b"
    assert t["decision"]["tie"] is None
    assert t["prompts"]["a"] == PROMPT and t["prompts"]["b"] == f"BRIEF: {PROMPT}\n"
    assert t["arms"]["b"]["check"]["passed"] and not t["arms"]["a"]["check"]["passed"]
    assert t["arms"]["a"]["tokens"] == 1000 + len(PROMPT) + 10 and t["task"]["answers"]["why"] == "Keep CI honest"
    assert t["task"]["questions"] == [{"skill": f"skill:{SKILL}", "q": QUESTION, "a": "It feeds the release notes"}]
    assert t["task"]["listed"] == {f"skill:{SKILL}": 1} and t["task"]["answers"]["stretch"] == ""
    assert t["fidelity"] == {"b": {"added": False, "dropped": False, "changed": False}}
    assert t["versions"] == {"worker": "fake-codex 1.0", "rewriter": "fake-codex 1.0", "asker": "fake-codex 1.0"}
    assert "+brief" in Path(t["output"], "b.diff").read_text() and f"apply {t['output']}/b.diff" in err
    calls = agents()
    assert [c["role"] for c in calls] == ["asker", "rewriter", "worker", "worker"]
    assert all(not {"ANTHROPIC_API_KEY", "OPENAI_BASE_URL"} & set(c["keys"]) for c in calls)
    assert "read-only" in calls[0]["argv"] and "--output-schema" in calls[0]["argv"]
    assert "read-only" in calls[1]["argv"] and "workspace-write" in calls[2]["argv"]
    assert "sk-ant-test-0123456789" not in Path(os.environ["BRIEFBENCH_HOME"], "log.jsonl").read_text()


def test_the_evaluation_stays_hidden_from_both_arms(agents, repo):
    """The goal and the check judge the results; the brief gets only your answers to the skill's own questions."""
    init(repo)
    assert bench(["ab", PROMPT], ANSWERS, cwd=repo)[0] == 0
    [t] = entries()
    request = Path(t["output"], "rewrite-b.request.md").read_text()
    assert "Answer: It feeds the release notes" in request and QUESTION in request and "<skill>" in request
    for hidden in ("Keep CI honest", "grep -q brief result.txt"):
        assert hidden not in request and all(hidden not in p for p in t["prompts"].values())
    asked = Path(t["output"], "questions-1.request.md").read_text()
    assert f"<prompt>\n{PROMPT}\n</prompt>" in asked and "Keep CI honest" not in asked


def test_a_skill_that_asks_nothing_gets_no_answers(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_ASKER", "none")
    init(repo)
    code, err = bench(["ab", PROMPT], answers(skill=None), cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["task"]["questions"] == [] and "No question to ask." in err
    assert "The skill asked no questions." in Path(t["output"], "rewrite-b.request.md").read_text()


def test_the_skill_may_ask_at_most_three(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_ASKER", "many")
    init(repo)
    code, err = bench(["ab", PROMPT], answers(skill="one\ntwo\nthree"), cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert [x["a"] for x in t["task"]["questions"]] == ["one", "two", "three"]
    assert t["task"]["listed"] == {f"skill:{SKILL}": 5} and "only the first 3 are asked" in err


def test_clarified_gets_the_same_answers_unrewritten(agents, repo):
    code, err = init(repo, a="clarified")
    assert code == 0, err
    code, err = bench(["ab", PROMPT], answers(check="test -f result.txt", after="1\n\nn\nn\nn\n"), cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["prompts"]["a"] == (f"{PROMPT}\n\nClarifying questions about this request, with my answers:\n"
                                 f"Q: {QUESTION}\nA: It feeds the release notes\n")
    assert t["prompts"]["b"] == f"BRIEF: {PROMPT}\n" and t["fidelity"] == {"b": {"added": False, "dropped": False,
                                                                               "changed": False}}
    assert [c["role"] for c in agents()] == ["asker", "rewriter", "worker", "worker"]


def test_clarified_lists_a_skipped_question_as_the_brief_sees_it(agents, repo):
    init(repo, a="clarified")
    assert bench(["ab", PROMPT], answers(skill=""), cwd=repo)[0] == 0
    [t] = entries()
    assert t["prompts"]["a"].endswith(f"Q: {QUESTION}\nA: (not answered)\n")
    assert f"- {QUESTION}\n  Answer: (skipped)" in Path(t["output"], "rewrite-b.request.md").read_text()


@pytest.mark.parametrize("a,b", [("clarified", "original"), ("clarified", "clarified")])
def test_clarified_needs_a_skill_in_the_other_arm(agents, repo, a, b):
    code, err = init(repo, a=a, b=b)
    assert code == 2 and "the other arm must be brief or skill:<folder>" in err


def test_two_skills_asking_the_same_question_ask_you_once(agents, repo, tmp_path):
    copy = tmp_path / "copy"
    shutil.copytree(SKILL, copy)
    (copy / "SKILL.md").write_text((copy / "SKILL.md").read_text().replace('version: "0.2.0"', 'version: "0.2.1"'))
    assert init(repo, a=f"skill:{copy}")[0] == 0
    code, err = bench(["ab", PROMPT], answers(check="test -f result.txt", after="t\ny\n\n" + "n\n" * 6), cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert [x["skill"] for x in t["task"]["questions"]] == [f"skill:{copy}", f"skill:{SKILL}"]
    asking = err.split("Asking the skill (1 of 2)", 1)[1].split("Your blind pick")[0]
    assert "random order" in err and str(copy) not in asking and str(SKILL) not in asking   # questions not labelled
    assert {x["a"] for x in t["task"]["questions"]} == {"It feeds the release notes"}
    assert set(t["fidelity"]) == {"a", "b"} and t["decision"]["tie"] == "both_acceptable"
    assert [c["role"] for c in agents()] == ["asker", "asker", "rewriter", "rewriter", "worker", "worker"]


def test_the_arms_work_apart_from_the_trials_records(agents, repo):
    """Neither worker can find the other arm's prompt, the brief or your answers next to its own folder."""
    init(repo)
    assert bench(["ab", PROMPT], ANSWERS, cwd=repo)[0] == 0
    [t] = entries()
    output = Path(t["output"])
    for call in agents():
        if call["role"] == "worker":
            cwd = Path(call["cwd"])
            assert output.parent not in cwd.parents and not (cwd.parent / "output").exists()
    assert Path(output, "a.prompt.md").read_text() == PROMPT and t["experiment_created"] == frozen()["created"]


def test_briefing_time_and_tokens_count_for_the_arm_that_needed_them(agents, repo):
    init(repo)
    assert bench(["ab", PROMPT], ANSWERS, cwd=repo)[0] == 0
    [t] = entries()
    assert t["arms"]["a"]["brief"] is None                       # the original needs no headless call
    assert t["arms"]["b"]["brief"]["tokens"] == (30 + 10) + (50 + 10)   # the fake asker and rewriter, as reported
    assert [c["step"] for c in t["task"]["headless"]] == ["questions-1", "rewrite-b"]


def test_none_runs_a_trial_without_the_repos_check_and_keeps_it(agents, repo):
    init(repo)
    assert bench(["ab", PROMPT], ANSWERS, cwd=repo)[0] == 0                # saves the check for the repo
    code, err = bench(["ab", PROMPT], answers(check="none", first=False, after="1\n\nn\nn\nn\n"), cwd=repo)
    assert code == 0, err
    second = entries()[1]
    assert second["settings"]["check"] == "" and second["arms"]["a"]["check"] is None and "Enter keeps it" in err
    repos = json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "repos.json").read_text())
    assert repos[str(repo)]["check"] == "grep -q brief result.txt"


@pytest.mark.parametrize("given,kept", [("tests/", ["tests"]), ("{repo}/tests, README.md", ["tests", "README.md"])])
def test_protected_paths_are_kept_relative_to_the_repo(agents, repo, given, kept):
    init(repo)
    typed = answers().replace("\ntests/\n", f"\n{given.format(repo=repo)}\n", 1)
    assert bench(["ab", PROMPT], typed, cwd=repo)[0] == 0
    assert entries()[0]["settings"]["protected"] == kept


def test_a_protected_path_outside_the_repo_is_asked_again(agents, repo):
    init(repo)
    typed = answers().replace("\ntests/\n", "\n../shared\ntests/\n", 1)
    code, err = bench(["ab", PROMPT], typed, cwd=repo)
    assert code == 0 and "../shared is outside the repo" in err
    assert entries()[0]["settings"]["protected"] == ["tests"]


def test_a_git_failure_after_the_arms_is_logged_as_failed(agents, repo, monkeypatch):
    init(repo)

    def broken(*args, **kwargs):
        raise cli.ConfigError("git diff failed in the worktree: index.lock exists")
    monkeypatch.setattr(cli.runner, "save_diff", broken)
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 3 and "index.lock" in err
    [f] = entries()
    assert (f["kind"], f["stage"]) == ("failed", "run") and f["task"]["questions"][0]["a"] == "It feeds the release notes"


def test_blind_pick_when_the_check_cant_decide(agents, repo):
    init(repo)
    code, err = bench(["ab", PROMPT], answers(goal="why", check="test -f result.txt", skill="", after="1\n2\n\n\n\n"),
                      cwd=repo)
    assert code == 0, err
    [t] = entries()
    d = t["decision"]
    assert (d["by"], d["pick"], d["guess"], d["winner"], d["tie"]) == ("you", "1", "2", d["sides"]["1"], None)
    assert t["fidelity"] == {"b": {"added": None, "dropped": None, "changed": None}}       # all skipped
    assert Path(t["output"], "side-1.diff").read_bytes() == Path(t["output"], f"{d['sides']['1']}.diff").read_bytes()
    assert "Side 1 was" in err and "BRIEF: " in err.split("Now check the brief")[1]


def test_a_task_that_isnt_handed_off_whole_is_excluded(agents, repo):
    init(repo)
    code, err = bench(["ab", "Carry on with what we discussed"], "y\n\n\n", cwd=repo)
    assert code == 0 and "exclusion" in err
    [e] = entries()
    assert e["kind"] == "excluded" and e["reasons"] == ["leans_on_chat"] and agents() == []
    assert not (Path(os.environ["BRIEFBENCH_HOME"]) / "trials").exists()


def test_protected_paths_are_put_back_and_fail_the_check(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "edit-tests")
    init(repo)
    code, err = bench(["ab", PROMPT], answers(goal="why", check="true", skill="", after="t\nn\n\nn\nn\nn\n"), cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert all(t["arms"][s]["protected_changed"] and not t["arms"][s]["check"]["passed"] for s in "ab")
    assert "test_x.py" not in Path(t["output"], "a.diff").read_text() and t["decision"]["winner"] == "tie"
    assert t["decision"]["tie"] == "both_unacceptable" and "neither good enough" in err


def test_a_changed_skill_is_refused(agents, repo, tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(SKILL, skill)
    init(repo, b=f"skill:{skill}")
    (skill / "SKILL.md").write_text((skill / "SKILL.md").read_text() + "\nOne more rule.\n")
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 3 and "changed" in err and entries() == [] and agents() == []


def test_a_changed_request_template_or_judge_prompt_is_refused(agents, repo, monkeypatch):
    init(repo)
    assert len(frozen()["templates"]["render"]) == 64 and frozen()["templates"]["judge"] is None
    original = treatments.REWRITE_REQUEST
    monkeypatch.setattr(treatments, "REWRITE_REQUEST", original + "\nBe brief.")
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 3 and "headless request templates differ" in err and agents() == []
    monkeypatch.setattr(treatments, "REWRITE_REQUEST", original)    # not undo(): that would also undo `hermetic`
    Path(os.environ["BRIEFBENCH_HOME"], "experiments", "exp.json").unlink()
    init_judged(repo)
    monkeypatch.setattr(judge, "template", lambda: "Pick the longer one. {goal} {a} {b}")
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 3 and "judge prompt differ" in err


def test_an_experiment_from_before_the_skills_own_questions_is_refused(agents, repo):
    init(repo)
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json"
    old = frozen()
    del old["render"], old["asker"]
    path.write_text(json.dumps(old))
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 3 and "older briefbench" in err and agents() == []


@pytest.mark.parametrize("variable,mode,words,roles", [
    ("FAKE_REWRITER", "nofence", "no brief", ["asker", "rewriter"]),
    ("FAKE_REWRITER", "write", "changed files", ["asker", "rewriter"]),
    ("FAKE_REWRITER", "fail", "rewrite failed", ["asker", "rewriter"]),
    ("FAKE_ASKER", "bad", "JSON asked for", ["asker"]),
    ("FAKE_ASKER", "write", "changed files", ["asker"]),
    ("FAKE_ASKER", "fail", "list of the skill's questions failed", ["asker"]),
])
def test_a_failed_headless_step_stops_the_trial_and_is_logged(agents, repo, monkeypatch, variable, mode, words,
                                                              roles):
    monkeypatch.setenv(variable, mode)
    init(repo)
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 4 and words in err
    [f] = entries()
    assert f["kind"] == "failed" and words in f["error"] and f["task"]["prompt"] == PROMPT and not f["aa"]
    assert f["treatments"] == {"a": "original", "b": f"skill:{SKILL}"}
    assert [c["role"] for c in agents()] == roles                # no worker ran
    assert f["stage"] == ("questions" if variable == "FAKE_ASKER" else "rewrite")


def test_arms_are_stopped_at_the_timeout(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "sleep")
    init(repo, "--timeout", "0.02")
    code, err = bench(["ab", PROMPT], answers(after="t\nn\n\nn\nn\nn\n"), cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["arms"]["a"]["timed_out"] and t["arms"]["b"]["timed_out"] and t["arms"]["a"]["seconds"] < 30


def test_noise_check_runs_treatment_a_in_both_arms(agents, repo):
    init(repo)
    code, err = bench(["ab", "--aa", PROMPT], answers(goal="why", check="test -f result.txt", skill=None, after="2\n"),
                      cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["kind"] == "aa" and t["prompts"]["a"] == t["prompts"]["b"] == PROMPT and t["decision"]["guess"] is None
    assert t["fidelity"] is None and t["task"]["questions"] == []
    assert [c["role"] for c in agents()] == ["worker", "worker"]          # A is the original: nothing to rewrite


def test_clean_removes_worktrees_and_keeps_the_output(agents, repo):
    init(repo)
    bench(["ab", PROMPT], ANSWERS, cwd=repo)
    [t] = entries()
    folder = Path(os.environ["BRIEFBENCH_HOME"]) / "worktrees" / t["id"]
    assert (folder / "a" / "result.txt").exists()
    code, err = bench(["clean"])
    assert code == 0 and "Removed 2 worktrees" in err
    assert not folder.exists() and Path(t["output"], "b.diff").exists()
    listed = subprocess.run(["git", "worktree", "list"], cwd=repo, capture_output=True, text=True).stdout
    assert str(folder) not in listed


def test_ab_needs_an_experiment_and_a_repo(agents, repo, tmp_path):
    assert bench(["ab", PROMPT], cwd=repo)[0] == 3                        # no experiment yet
    init(repo)
    (tmp_path / "plain").mkdir()
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=tmp_path / "plain")
    assert code == 3 and "git repo" in err


def init_judged(repo, judge="claude-code"):
    return bench(["init", "exp", "--b", f"skill:{SKILL}", "--worker", "codex", "--worker-model", "", "--rewriter",
                  "codex", "--rewriter-model", "", "--judge", judge, "--judge-model", "", "--cap", "50", "-y"], cwd=repo)


def test_the_judge_rules_after_your_pick_in_both_orders(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_JUDGE", "brief-wins")
    assert init_judged(repo)[0] == 0
    code, err = bench(["ab", PROMPT], answers(check="test -f result.txt", skill="", after="1\n\ny\nn\nn\nn\n"),
                      cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["judge"]["winner"] == "b" and sorted(o["verdict"] for o in t["judge"]["orders"]) == ["[[A>B]]", "[[B>A]]"]
    judged = [c for c in agents() if c["role"] == "judge"]
    assert len(judged) == 2 and all(c["name"] == "claude" and "--json-schema" in c["argv"] for c in judged)
    assert all(PROMPT not in c["argv"][-1] and "BRIEF:" not in c["argv"][-1] for c in judged)   # blind to treatments
    assert "Keep CI honest" in judged[0]["argv"][-1] and "B wins, in both orders" in err
    assert t["versions"]["judge"] == "fake-claude 1.0"
    output = Path(t["output"])
    for c in judged:                                     # an empty folder of its own, far from the trial's records
        assert output not in Path(c["cwd"]).parents and Path(c["cwd"]).name.startswith("order-")
        assert not Path(c["cwd"]).exists()               # removed afterwards
    assert sorted(p.name for p in (output / "judge").iterdir()) == ["order-1.err", "order-1.out", "order-2.err",
                                                                    "order-2.out"]


def test_score_prints_the_report(agents, repo):
    init(repo)
    bench(["ab", PROMPT], ANSWERS, cwd=repo)
    out = io.StringIO()
    assert cli.run(["score"], stdout=out, stderr=io.StringIO()) == 0
    text = out.getvalue()
    assert "Trials: 1. B won 1, A won 0, 0 ties." in text and "Verdict: none yet." in text
    assert "Fidelity reviews of B's briefs: 0 of 1 failed" in text
    out = io.StringIO()
    assert cli.run(["score", "--json"], stdout=out, stderr=io.StringIO()) == 0
    summary = json.loads(out.getvalue())
    assert (summary["wins_b"], summary["trials"], summary["verdict"]["state"]) == (1, 1, "collecting")
    assert summary["trial_ids"] == [entries()[0]["id"]]


def test_a_judge_failure_never_stops_a_trial(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_JUDGE", "fail")
    init_judged(repo)
    code, err = bench(["ab", PROMPT], answers(check="test -f result.txt", skill="", after="t\ny\n\ny\nn\nn\nn\n"),
                      cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["judge"]["winner"] is None and "judge failed" in t["judge"]["error"] and "yours alone" in err


def test_the_judge_waits_for_your_ok_for_each_repo(agents, repo):
    init_judged(repo)
    code, err = bench(["ab", PROMPT], answers(check="test -f result.txt", skill="", after="1\n\nn\nn\nn\nn\n"),
                      cwd=repo)
    assert code == 0, err
    code, err = bench(["ab", PROMPT], answers(check="", skill="", first=False, after="2\n\nn\nn\nn\n"),
                      cwd=repo)                                          # not asked again
    assert code == 0, err
    assert [e["judge"] for e in entries()] == [None, None] and not [c for c in agents() if c["role"] == "judge"]
    assert entries()[1]["settings"]["check"] == "test -f result.txt"     # Enter kept the repo's check


def test_the_judge_must_come_from_a_third_vendor(agents, repo):
    code, err = init_judged(repo, judge="codex")
    assert code == 2 and "neither the worker's vendor nor the rewriter's" in err


def test_trial_folders_are_private(agents, repo):
    init(repo)
    assert bench(["ab", PROMPT], ANSWERS, cwd=repo)[0] == 0
    [t] = entries()
    home = Path(os.environ["BRIEFBENCH_HOME"])
    for folder in (home / "trials", home / "trials" / t["id"], Path(t["output"]), home / "worktrees",
                   home / "worktrees" / t["id"]):
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700, folder


def test_a_judge_tie_in_both_orders_is_not_called_a_flip(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_JUDGE", "[[A=B]]")
    init_judged(repo)
    code, err = bench(["ab", PROMPT], answers(check="test -f result.txt", skill="", after="t\ny\n\ny\nn\nn\nn\n"),
                      cwd=repo)
    assert code == 0, err
    assert entries()[0]["judge"]["winner"] == "tie" and "a tie in both orders" in err and "changed with" not in err

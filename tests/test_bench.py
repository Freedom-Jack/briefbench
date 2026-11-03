"""init, ab and clean end to end, through fake agent CLIs (tests/fake_agent.py) in a throwaway git repo."""
import io
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from briefbench import cli
from briefbench.log import read_entries

SKILL = Path(__file__).resolve().parents[1] / "skills" / "brief"
PROMPT = "Make result.txt say what it is"
# 3 eligibility questions, task type, setup and protected paths (first trial in a repo), why, check, stretch
ANSWERS = "\n\n\ncode\n\ntests/\nKeep CI honest\ngrep -q brief result.txt\n\n"


def bench(argv, answers="", cwd=None):
    err = io.StringIO()
    return cli.run(argv, stdin=io.StringIO(answers), stderr=err, cwd=cwd), err.getvalue()


def entries():
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def init(repo, *extra, b=f"skill:{SKILL}"):
    return bench(["init", "exp", "--a", "original", "--b", b, "--worker", "codex", "--worker-model", "",
                  "--rewriter", "codex", "--rewriter-model", "", "--cap", "50", "-y", *extra], cwd=repo)


def test_init_freezes_the_experiment_once(agents, repo):
    code, err = init(repo)
    assert code == 0, err
    exp = json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / "exp.json").read_text())
    assert exp["b"]["kind"] == "skill" and exp["b"]["version"] == "0.1.0" and len(exp["b"]["sha256"]) == 64
    assert exp["worker"]["agent"] == "codex" and exp["worker"]["argv"][-2:] == ["--", "{prompt}"]
    assert exp["rule"]["adopt_first"] == 16 and exp["cap_percent"] == 50
    assert init(repo)[0] == 2                                    # frozen settings are never changed
    assert stat.S_IMODE(Path(os.environ["BRIEFBENCH_HOME"]).stat().st_mode) == 0o700


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
    assert t["prompts"]["a"] == PROMPT and t["prompts"]["b"] == f"BRIEF: {PROMPT}\n"
    assert t["arms"]["b"]["check"]["passed"] and not t["arms"]["a"]["check"]["passed"]
    assert t["arms"]["a"]["tokens"] == 1000 + len(PROMPT) + 10 and t["task"]["answers"]["why"] == "Keep CI honest"
    assert "+brief" in Path(t["output"], "b.diff").read_text() and f"apply {t['output']}/b.diff" in err
    calls = agents()
    assert [c["role"] for c in calls] == ["rewriter", "worker", "worker"]
    assert all(not {"ANTHROPIC_API_KEY", "OPENAI_BASE_URL"} & set(c["keys"]) for c in calls)
    assert "read-only" in calls[0]["argv"] and "workspace-write" in calls[1]["argv"]
    assert "sk-ant-test-0123456789" not in Path(os.environ["BRIEFBENCH_HOME"], "log.jsonl").read_text()


def test_blind_pick_when_the_check_cant_decide(agents, repo):
    init(repo)
    code, err = bench(["ab", PROMPT], "\n\n\ncode\n\n\nwhy\ntest -f result.txt\n\n1\n2\n", cwd=repo)
    assert code == 0, err
    [t] = entries()
    d = t["decision"]
    assert (d["by"], d["pick"], d["guess"], d["winner"]) == ("you", "1", "2", d["sides"]["1"])
    assert Path(t["output"], "side-1.diff").read_bytes() == Path(t["output"], f"{d['sides']['1']}.diff").read_bytes()
    assert "Side 1 was" in err


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
    code, err = bench(["ab", PROMPT], "\n\n\ncode\n\ntests/\nwhy\ntrue\n\nt\n\n", cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert all(t["arms"][s]["protected_changed"] and not t["arms"][s]["check"]["passed"] for s in "ab")
    assert "test_x.py" not in Path(t["output"], "a.diff").read_text() and t["decision"]["winner"] == "tie"


def test_a_changed_skill_is_refused(agents, repo, tmp_path):
    skill = tmp_path / "skill"
    shutil.copytree(SKILL, skill)
    init(repo, b=f"skill:{skill}")
    (skill / "SKILL.md").write_text((skill / "SKILL.md").read_text() + "\nOne more rule.\n")
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 3 and "changed" in err and entries() == [] and agents() == []


@pytest.mark.parametrize("mode,words", [("nofence", "no brief"), ("write", "changed files"),
                                        ("fail", "rewrite failed")])
def test_a_bad_headless_rewrite_stops_the_trial(agents, repo, monkeypatch, mode, words):
    monkeypatch.setenv("FAKE_REWRITER", mode)
    init(repo)
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=repo)
    assert code == 4 and words in err and entries() == []
    assert [c["role"] for c in agents()] == ["rewriter"]         # no worker ran


def test_arms_are_stopped_at_the_timeout(agents, repo, monkeypatch):
    monkeypatch.setenv("FAKE_WORKER", "sleep")
    init(repo, "--timeout", "0.02")
    code, err = bench(["ab", PROMPT], ANSWERS + "t\n\n", cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["arms"]["a"]["timed_out"] and t["arms"]["b"]["timed_out"] and t["arms"]["a"]["seconds"] < 30


def test_noise_check_runs_treatment_a_in_both_arms(agents, repo):
    init(repo)
    code, err = bench(["ab", "--aa", PROMPT], "\n\n\ncode\n\n\nwhy\ntest -f result.txt\n\n2\n", cwd=repo)
    assert code == 0, err
    [t] = entries()
    assert t["kind"] == "aa" and t["prompts"]["a"] == t["prompts"]["b"] == PROMPT and t["decision"]["guess"] is None
    assert [c["role"] for c in agents()] == ["worker", "worker"]          # A is the original: nothing to rewrite


def test_clean_removes_worktrees_and_keeps_the_output(agents, repo):
    init(repo)
    bench(["ab", PROMPT], ANSWERS, cwd=repo)
    folder = Path(entries()[0]["output"]).parent
    assert (folder / "a" / "result.txt").exists()
    code, err = bench(["clean"])
    assert code == 0 and "Removed 2 worktrees" in err
    assert not (folder / "a").exists() and (folder / "output" / "b.diff").exists()
    listed = subprocess.run(["git", "worktree", "list"], cwd=repo, capture_output=True, text=True).stdout
    assert str(folder) not in listed


def test_ab_needs_an_experiment_and_a_repo(agents, repo, tmp_path):
    assert bench(["ab", PROMPT], cwd=repo)[0] == 3                        # no experiment yet
    init(repo)
    (tmp_path / "plain").mkdir()
    code, err = bench(["ab", PROMPT], ANSWERS, cwd=tmp_path / "plain")
    assert code == 3 and "git repo" in err

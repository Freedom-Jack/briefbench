"""scripts/review_briefs.py and score's fidelity policy: reviews of briefs from unattended trials, made apart from the
outcomes, offline through fake agent CLIs (tests/fake_agent.py)."""
import importlib.util
import io
import json
import os
from pathlib import Path

from briefbench import cli, experiment, score
from briefbench.log import read_entries

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "brief"
_spec = importlib.util.spec_from_file_location("review_briefs", ROOT / "scripts" / "review_briefs.py")
review = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(review)
FACTS = ["The report goes to the board on Monday.", "Only customers who signed up in 2026 count."]


def bench(argv, cwd=None):
    err = io.StringIO()
    return cli.run(argv, stdin=io.StringIO(""), stderr=err, cwd=cwd), err.getvalue()


def entries():
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def stand_in(repo, *extra, b=None):
    return bench(["init", "exp", "--a", "original", "--b", b or f"skill:{SKILL}", "--worker", "claude-code",
                  "--worker-model", "", "--rewriter", "claude-code", "--rewriter-model", "", "--judge", "none",
                  "--cap", "50", "--rule", "fixed:10", "--net-min", "0", "--scoring", "check", "-y", *extra], cwd=repo)


def trials(tmp_path, repo, count, *extra):
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"format": 1, "id": "t-001", "set": "demo/1", "repo": str(repo), "facts": FACTS,
                                "prompt": "Make result.txt say what it is", "type": "analysis",
                                "goal": "Say what it is", "check": "grep -q brief result.txt"}))
    for _ in range(count):
        code, err = bench(["ab", "--task", str(path), *extra], cwd=tmp_path)
        assert code == 0, err


def reviewed(typed):
    out, err = io.StringIO(), io.StringIO()
    code = review.main(["--experiment", "exp"], stdin=io.StringIO(typed), stdout=out)
    return code, out.getvalue()


def verdict():
    return score.summary(experiment.load("exp", os.environ), entries())


def test_reviews_made_apart_from_the_outcomes_clear_the_wait(agents, repo, tmp_path):
    assert stand_in(repo)[0] == 0
    trials(tmp_path, repo, 3)
    assert "3 of the 3 briefs chosen for review have no fidelity review yet" in verdict()["verdict"]["blocked_by"]
    code, shown = reviewed("n\nn\nn\n" * 3)
    assert code == 0
    assert "Make result.txt say what it is" in shown and f"A: {FACTS[0]}" in shown and "BRIEF:" in shown
    assert "stand-in requester" in shown
    assert not any(word in shown for word in ("passed", "wins", " tie", "check", "diff"))     # no outcome at all
    lines = [e for e in entries() if e["kind"] == "fidelity"]
    assert len(lines) == 3 and {e["side"] for e in lines} == {"b"}
    s = verdict()
    assert not any("fidelity" in b for b in s["verdict"]["blocked_by"])
    assert s["fidelity"]["b"]["reviewed"] == 3 and s["fidelity_review"]["waiting"] == 0
    assert reviewed("")[0] == 0                                            # nothing left to review


def test_unfaithful_briefs_block_only_beyond_the_frozen_tolerance(agents, repo, tmp_path):
    assert stand_in(repo, "--unfaithful-max", "1")[0] == 0
    assert experiment.load("exp", os.environ)["fidelity_policy"] == {"sample": None, "max_unfaithful": 1}
    trials(tmp_path, repo, 2)
    assert reviewed("y\nn\nn\n" + "n\nn\nn\n")[0] == 0                       # one brief adds something
    s = verdict()
    assert s["fidelity_review"]["unfaithful"] == 1 and not any("fidelity" in b for b in s["verdict"]["blocked_by"])


def test_by_default_one_unfaithful_brief_blocks(agents, repo, tmp_path):
    assert stand_in(repo)[0] == 0
    trials(tmp_path, repo, 1)
    assert reviewed("n\ny\nn\n")[0] == 0
    assert ("1 of the briefs chosen for review failed your fidelity review, and at most 0 may"
            in verdict()["verdict"]["blocked_by"])


def test_a_sample_is_drawn_from_the_experiment_once_all_trials_are_in(agents, repo, tmp_path):
    assert stand_in(repo, "--review-sample", "3")[0] == 0
    trials(tmp_path, repo, 2)
    code, _ = reviewed("")
    assert code == 2                                                       # not before all 10 trials are in
    trials(tmp_path, repo, 8)
    exp = experiment.load("exp", os.environ)
    _all, used, _ = score._used(exp, score._lines(exp, entries()))
    chosen = [t["id"] for t in score._chosen(exp, used)]
    assert len(chosen) == 3 and chosen == [t["id"] for t in score._chosen(exp, used)]     # the same every time
    assert "3 of the 3 briefs chosen for review" in " ".join(verdict()["verdict"]["blocked_by"])
    code, shown = reviewed("n\nn\nn\n" * 3)
    assert code == 0 and shown.count("Brief ") == 3
    assert {e["trial"] for e in entries() if e["kind"] == "fidelity"} == set(chosen)
    assert verdict()["fidelity_review"]["waiting"] == 0


def test_stopping_early_keeps_the_reviews_made(agents, repo, tmp_path):
    assert stand_in(repo)[0] == 0
    trials(tmp_path, repo, 2)
    assert reviewed("n\nn\nn\n")[0] == 130
    assert len([e for e in entries() if e["kind"] == "fidelity"]) == 1
    assert "1 of the 2 briefs chosen for review has no fidelity review yet" in verdict()["verdict"]["blocked_by"]


def test_the_policy_goes_with_a_skill_run_from_task_files(agents, repo, tmp_path):
    tip = tmp_path / "tip.md"
    tip.write_text("BRIEF: be careful.\n")
    code, err = stand_in(repo, "--review-sample", "5", b=f"snippet:{tip}")
    assert code == 2 and "go with a skill treatment and --scoring check" in err
    assert stand_in(repo, b=f"snippet:{tip}")[0] == 0
    assert experiment.load("exp", os.environ)["fidelity_policy"] is None
    assert reviewed("")[0] == 2                                            # nothing to review apart from outcomes


def test_single_arm_briefs_can_be_reviewed_without_becoming_paired_evidence(agents, repo, tmp_path):
    assert stand_in(repo)[0] == 0
    trials(tmp_path, repo, 1, "--only", "a")
    trials(tmp_path, repo, 2, "--only", "b")
    exp = experiment.load("exp", os.environ)
    queue, why = score.review_queue(exp, entries())
    assert why is None and len(queue) == 2
    assert {r["side"] for r in queue} == {"b"}
    code, shown = reviewed("n\nn\nn\n" * 2)
    assert code == 0 and shown.count("Brief ") == 2
    assert not any(word in shown for word in ("passed", "wins", " tie", "check", "diff"))
    assert {r["trial"] for r in entries() if r["kind"] == "fidelity"} == {r["id"] for r in queue}
    assert score.review_queue(exp, entries()) == ([], None)
    assert score._used(exp, score._lines(exp, entries()))[1] == []
    assert reviewed("")[0] == 0


def test_single_arm_reviews_do_not_reinterpret_a_paired_sampling_policy(agents, repo, tmp_path):
    assert stand_in(repo, "--review-sample", "3")[0] == 0
    trials(tmp_path, repo, 1, "--only", "b")
    queue, why = score.review_queue(experiment.load("exp", os.environ), entries())
    assert queue == [] and "paired-trial sampling policy" in why
    assert reviewed("")[0] == 2

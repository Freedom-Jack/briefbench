"""Real agent CLI calls on your subscriptions. Deselected by default; run with: uv run pytest -m live -v -rA
Each test runs once per agent CLI, and skips one that isn't installed or isn't logged in with a plan."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from briefbench import judge, treatments
from briefbench.presets import AGENTS, agent_env

pytestmark = pytest.mark.live
SKILL = Path(__file__).resolve().parents[1] / "skills" / "brief"
GOOD = ("--- a/stats.py\n+++ b/stats.py\n@@ -1,2 +1,4 @@\n def mean(xs):\n+    if not xs:\n+        return 0.0\n"
        "     return sum(xs) / len(xs)\n")
BAD = "--- a/stats.py\n+++ b/stats.py\n@@ -1,2 +1,2 @@\n def mean(xs):\n-    return sum(xs) / len(xs)\n+    return 0.0\n"


def caller(name, role, folder, **slots):
    agent = AGENTS[name]
    executable = agent.find()
    if not executable:
        pytest.skip(f"{name} isn't installed")
    report = subprocess.run([executable, *agent.login], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                            env=agent_env(os.environ), timeout=60)
    if not agent.on_plan(report.stdout + report.stderr):
        pytest.skip(f"{name} isn't logged in with a plan")

    def call(prompt):
        done = subprocess.run(agent.argv(executable, role, prompt=prompt, **slots), cwd=folder, capture_output=True,
                              text=True, stdin=subprocess.DEVNULL, env=agent_env(os.environ), timeout=600)
        reply = agent.parse(done.stdout)
        assert done.returncode == 0 and not reply.error, done.stderr[-2000:]
        print(f"{name} {role}: {reply.tokens} tokens, model {reply.model or 'not reported'}")
        return reply.text
    return call


@pytest.mark.parametrize("name", sorted(AGENTS))
def test_live_judge(name, tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps(judge.SCHEMA))
    call = caller(name, "judge", tmp_path, schema=str(schema), schema_json=json.dumps(judge.SCHEMA))
    sides = {"1": judge.material(BAD, {"passed": False, "exit_code": 1}, "AssertionError: mean([1, 2, 3]) == 2", False),
             "2": judge.material(GOOD, {"passed": True, "exit_code": 0}, "", False)}
    ruling = judge.rule("mean() returns 0.0 for an empty list, and still works for other lists", sides, call)
    print(json.dumps(ruling, indent=2))                    # shown with -rA, for a person to read
    assert ruling["winner"] == "2" and all(order["verdict"] in judge.LABELS for order in ruling["orders"])


@pytest.mark.parametrize("name", sorted(AGENTS))
def test_live_headless_rewrite(name, tmp_path):
    """The two headless steps: the questions the skill would ask, in turns, then the brief from answers to them."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    schema = tmp_path / "questions.schema.json"                  # outside the repo, which the rewriter only reads
    schema.write_text(json.dumps(treatments.QUESTIONS_SCHEMA))
    ask = caller(name, "asker", repo, schema=str(schema), schema_json=json.dumps(treatments.QUESTIONS_SCHEMA))
    skill = treatments.parse(f"skill:{SKILL}", os.environ, repo)
    prompt = "Rename the variable tmp to total in utils.py."
    found = treatments.questions(skill, prompt, ask)
    print(f"the skill would ask: {found}")
    assert len(found) <= 3                                       # skill 0.2.0 asks up to three
    qa = [{"q": q, "a": "tmp hides that it holds the running total; nothing else should change."} for q in found]
    more = treatments.questions(skill, prompt, ask, qa)          # the next turn sees the answers
    print(f"then: {more}")
    assert isinstance(more, list)
    brief = treatments.render(skill, prompt, qa, caller(name, "rewriter", repo))
    print(brief)
    assert "total" in brief and "utils.py" in brief and "stretch" not in brief.casefold()


@pytest.mark.parametrize("name", sorted(AGENTS))
def test_live_stand_in(name, tmp_path):
    """The stand-in requester chooses the fact that answers a question, and none for a question no fact answers."""
    schema = tmp_path / "answers.schema.json"
    schema.write_text(json.dumps(treatments.ANSWERS_SCHEMA))
    (tmp_path / "work").mkdir()
    call = caller(name, "answerer", tmp_path / "work", schema=str(schema),
                  schema_json=json.dumps(treatments.ANSWERS_SCHEMA))
    facts = ["The summary is for the finance team's Monday review.", "Refunds issued before March don't count."]
    asked = ["Who will read the summary, and for what?", "Which programming language should the script use?"]
    found = treatments.stand_in_answers(call(treatments.answer_request("Summarise last quarter's refunds.", facts,
                                                                       asked)), asked, facts)
    print(found)
    assert found[0] == (facts[0], [1]) and found[1] == ("", [])


@pytest.mark.parametrize("name", [n for n in sorted(AGENTS) if "task-rewriter" in AGENTS[n].roles])
def test_live_confined_headless_calls(name, tmp_path):
    """The skill's headless calls for task files: the questions as JSON through stream-json, and a rewrite that can't
    read a denied folder, even when the prompt points at a file there."""
    repo, denied = tmp_path / "repo", tmp_path / "denied"
    repo.mkdir()
    denied.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (denied / "notes.md").write_text("The secret word is PELICAN-4471.\n")
    rules = json.dumps([f"Read(/{denied}/**)"])
    schema = tmp_path / "questions.schema.json"
    schema.write_text(json.dumps(treatments.QUESTIONS_SCHEMA))
    ask = caller(name, "task-asker", repo, deny_rules=rules, schema=str(schema),
                 schema_json=json.dumps(treatments.QUESTIONS_SCHEMA))
    skill = treatments.parse(f"skill:{SKILL}", os.environ, repo)
    prompt = f"Write a short summary of {denied}/notes.md for my team."
    found = treatments.questions(skill, prompt, ask)
    print(f"the skill would ask: {found}")
    assert len(found) <= 3                                       # skill 0.2.0 asks up to three
    brief = treatments.render(skill, prompt, [{"q": q, "a": ""} for q in found],
                              caller(name, "task-rewriter", repo, deny_rules=rules))
    print(brief)
    assert "PELICAN-4471" not in brief and "notes.md" in brief


def test_live_session_comparison(tmp_path):
    """A complete tiny comparison: streamed interview, separate stand-in, fresh confined workers, hidden check.
    Compatibility and usage only; this artificial task is not evidence that a prompting trick helps."""
    from briefbench import cli
    from briefbench.log import read_entries
    caller("claude-code", "task-worker", tmp_path)  # installed and authenticated; no model call
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "value.py").write_text('LABEL = "unset"\n')
    for args in (["init", "-q"], ["add", "."], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
        subprocess.run(["git", *args], cwd=repo, check=True)
    task = tmp_path / "keys" / "one" / "task.json"
    task.parent.mkdir(parents=True)
    task.write_text(json.dumps({"format": 1, "id": "smoke", "set": "smoke/1", "stratum": "gap",
                               "repo": str(repo), "type": "code", "prompt": "Set LABEL in value.py to my chosen label. The label is private and unavailable in the repo.",
                               "goal": "The chosen label is used.", "facts": ["My chosen label is ORCHID-719."],
                               "check": "python3 -c 'from value import LABEL; assert LABEL == \"ORCHID-719\"'"}))
    model = AGENTS["claude-code"].default_model
    assert cli.run(["init", "session-smoke", "--a", "original", "--b", f"skill:{SKILL}", "--worker", "claude-code",
                    "--worker-model", model, "--rewriter", "claude-code", "--rewriter-model", model, "--judge", "none",
                    "--cap", "100", "--timeout", "3", "--scoring", "check", "--rule", "fixed:10", "--net-min", "0",
                    "--interview", "session", "--pin-versions", "-y"]) == 0
    try:
        assert cli.run(["ab", "--experiment", "session-smoke", "--task", str(task)]) == 0
        [row] = read_entries(Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl")
        assert row["arms"]["b"]["check"]["passed"]
        assert not any(a["looked_outside"] for a in row["arms"].values())
        assert row["task"]["questions"] and not any(c["step"].startswith("rewrite") for c in row["task"]["headless"])
        calls = [*row["arms"].values(), *row["task"]["headless"]]
        print("Complete smoke comparison:", len(calls), "turns,", sum(c["tokens"] for c in calls), "tokens,",
              sum(c["cost_usd"] for c in calls), "CLI USD estimate")
    finally:
        cli.run(["clean"])

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
    """The two headless steps: the questions the skill would ask, then the brief from answers to them."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    schema = tmp_path / "questions.schema.json"                  # outside the repo, which the rewriter only reads
    schema.write_text(json.dumps(treatments.QUESTIONS_SCHEMA))
    ask = caller(name, "asker", repo, schema=str(schema), schema_json=json.dumps(treatments.QUESTIONS_SCHEMA))
    skill = treatments.parse(f"skill:{SKILL}", os.environ, repo)
    prompt = "Rename the variable tmp to total in utils.py."
    found, listed = treatments.questions(skill, prompt, ask)
    print(f"the skill would ask: {found}")
    assert listed <= 3                                           # the skill asks at most three
    qa = [{"q": q, "a": "tmp hides that it holds the running total; nothing else should change."} for q in found]
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
    found, listed = treatments.questions(skill, prompt, ask)
    print(f"the skill would ask: {found}")
    assert listed <= 3
    brief = treatments.render(skill, prompt, [{"q": q, "a": ""} for q in found],
                              caller(name, "task-rewriter", repo, deny_rules=rules))
    print(brief)
    assert "PELICAN-4471" not in brief and "notes.md" in brief

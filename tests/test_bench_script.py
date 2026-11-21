"""scripts/bench.py: the bench's fixed tasks, the plain prompt's shared runs, a trick's runs and the table, through fake
agent CLIs (tests/fake_agent.py) and a stand-in generator. The fake worker writes "brief" into result.txt when its
prompt holds BRIEF, and "original" otherwise."""
import contextlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path

import pytest

from briefbench.log import read_entries

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("bench_script", ROOT / "scripts" / "bench.py")
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

# A stand-in for a materials generator, with the same command shape: three kinds of task, each with its own check.
# up: the plain prompt fails and a trick with BRIEF in it passes; down: the other way round; ask: like up, but its
# check needs the requester's answers, so text added to the prompt is never run there.
GENERATOR = '''
import argparse, json, subprocess, sys
from pathlib import Path
p = argparse.ArgumentParser()
m = p.add_subparsers(dest="cmd").add_parser("make")
m.add_argument("--seed", type=int)
for kind in ("up", "down", "ask"):
    m.add_argument(f"--{kind}", type=int, default=0)
m.add_argument("--out", type=Path)
m.add_argument("--keys", type=Path)
a = p.parse_args()
if a.out.exists() or a.keys.exists():
    sys.exit("both folders must be new")
checks = {"up": "grep -q brief result.txt", "down": "grep -q original result.txt", "ask": "grep -q brief result.txt"}
names = []
for kind in ("up", "down", "ask"):
    for i in range(getattr(a, kind)):
        name = f"{kind}-{a.seed}-{i}"
        repo = a.out / name
        repo.mkdir(parents=True)
        (repo / "README.md").write_text(name + "\\n")
        for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i"]):
            subprocess.run(["git", *args], cwd=repo, check=True)
        (a.keys / name).mkdir(parents=True)
        (a.keys / name / "task.json").write_text(json.dumps({
            "format": 1, "id": name, "set": "demo/1", "stratum": kind, "repo": str(repo),
            "prompt": "Make result.txt say what it is", "type": "code", "goal": "Say what it is",
            "check": checks[kind], "generator_sha256": "g" * 64, "checker_sha256": "c" * 64}))
        names.append(f"{name}/task.json")
(a.keys / "tasks.txt").write_text("".join(n + "\\n" for n in names))
'''


def kind(name, tasks, needs_answers=False):
    return {"name": name, "flag": f"--{name}", "tasks": tasks, "needs_answers": needs_answers, "label": name.title(),
            "about": f"the {name} tasks"}


@pytest.fixture
def setup(tmp_path, monkeypatch, agents):
    """A recipe with one set of six tasks (3 up, 2 down, 1 ask) and one set whose generator isn't there yet, a trick
    list, and the table written into tmp_path."""
    generator = tmp_path / "gen.py"
    generator.write_text(GENERATOR)
    recipe = {"format": 1, "name": "bench-t", "about": "a test bench",
              "worker": {"agent": "claude-code", "model": "fake-model-1"}, "timeout_minutes": 5,
              "sets": [{"set": "demo/1", "generator": str(generator), "seed": 7, "work": "coding",
                        "kinds": [kind("up", 3), kind("down", 2), kind("ask", 1, True)]},
                       {"set": "later/1", "generator": "scripts/materials/not_yet.py", "seed": 8, "work": "coding",
                        "kinds": [kind("more", 2)]}]}
    tip = tmp_path / "tip.md"
    tip.write_text("BRIEF: aim higher.\n")
    tricks = {"format": 1, "tricks": [
        {"id": "tip", "treatment": f"snippet:{tip}", "kinds": ["demo/1:up"]},
        {"id": "tip-down", "treatment": f"snippet:{tip}", "kinds": ["demo/1:down"]},
        {"id": "later", "treatment": None, "kinds": ["later/1:more"], "waits": "its tasks, in another session"}]}
    paths = {"recipe": tmp_path / "recipe.json", "tricks": tmp_path / "tricks.json", "tip": tip,
             "board": tmp_path / "board.md"}
    paths["recipe"].write_text(json.dumps(recipe))
    paths["tricks"].write_text(json.dumps(tricks))
    monkeypatch.setattr(bench, "TRICKS", paths["tricks"])
    monkeypatch.setattr(bench, "BOARD", paths["board"])
    return paths


def main(paths, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bench.main(["--bench", str(paths["recipe"]), *argv])
    return code, out.getvalue() + err.getvalue()


def entries():
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "log.jsonl"
    return read_entries(path) if path.exists() else []


def test_make_makes_the_tasks_once_and_a_set_waits_for_its_generator(setup):
    code, said = main(setup, "make")
    assert code == 0, said
    assert "later/1: waits for scripts/materials/not_yet.py" in said and "has 6 tasks" in said
    folder = Path(os.environ["BRIEFBENCH_HOME"]) / "bench" / "bench-t"
    listed = (folder / "tasks.txt").read_text().splitlines()
    assert len(listed) == 6 and all(line.startswith("demo-1/keys/") for line in listed)
    assert [t["stratum"] for t in bench.bench_tasks(json.loads(setup["recipe"].read_text()))] == \
        ["up", "up", "up", "down", "down", "ask"]
    assert main(setup, "make")[0] == 0                  # a set once made is kept, never made again
    assert (folder / "tasks.txt").read_text().splitlines() == listed


def test_make_refuses_tasks_that_no_longer_match_the_recipe(setup):
    assert main(setup, "make")[0] == 0
    recipe = json.loads(setup["recipe"].read_text())
    recipe["sets"][0]["kinds"][0]["tasks"] = 4
    setup["recipe"].write_text(json.dumps(recipe))
    code, said = main(setup, "make")
    assert code == 1 and "don't match the recipe" in said


def test_the_plain_prompt_asks_first_then_runs_twice_on_each_task_and_picks_up_where_it_stopped(setup):
    assert main(setup, "make")[0] == 0
    code, said = main(setup, "plain")
    assert code == 0 and "12 runs, about" in said and "Nothing was run" in said and entries() == []
    code, said = main(setup, "plain", "--yes", "--limit", "2")
    assert code == 0, said
    assert [e["kind"] for e in entries()] == ["aa", "aa"]
    assert main(setup, "plain", "--yes")[0] == 0
    lines = entries()
    assert len(lines) == 6 and {e["experiment"] for e in lines} == {"bench-t.plain"}
    assert {e["treatments"]["a"] for e in lines} == {"original"} and len({bench.sha(e) for e in lines}) == 6
    code, said = main(setup, "plain", "--yes")
    assert code == 0 and "has run on every task" in said and len(entries()) == 6


def test_a_trick_waits_for_the_plain_prompts_runs(setup):
    assert main(setup, "make")[0] == 0
    code, said = main(setup, "run", "tip", "--yes")
    assert code == 2 and "Run the plain prompt on every task first" in said and entries() == []


def test_a_trick_runs_once_on_each_task_it_can_change_under_an_experiment_named_by_its_hash(setup):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    code, said = main(setup, "run", "tip", "--yes")
    assert code == 0, said
    assert "once on each of 5 tasks" in said                   # not the ask task: added text can't ask anyone
    runs = [e for e in entries() if e["kind"] == "run"]
    assert len(runs) == 5 and {e["side"] for e in runs} == {"b"}
    assert {e["task"]["source"]["stratum"] for e in runs} == {"up", "down"}
    [name] = {e["experiment"] for e in runs}
    assert re.fullmatch(r"bench-t\.tip-[0-9a-f]{8}", name)
    code, said = main(setup, "run", "tip", "--yes")
    assert code == 0 and "has run on every task it can change" in said
    setup["tip"].write_text("BRIEF: aim much higher.\n")       # an edited treatment is a new one, run afresh
    assert main(setup, "run", "tip", "--yes")[0] == 0
    assert len({e["experiment"] for e in entries() if e["kind"] == "run"}) == 2


def test_a_trick_with_no_room_runs_only_anyway_and_can_still_hurt(setup):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    code, said = main(setup, "run", "tip-down", "--yes")
    assert code == 0 and "No room" in said and not any(e["kind"] == "run" for e in entries())
    assert main(setup, "run", "tip-down", "--yes", "--anyway")[0] == 0
    assert sum(e["kind"] == "run" for e in entries()) == 5
    line = next(line for line in main(setup, "board")[1].splitlines() if line.startswith("| [tip-down]"))
    assert ("No room: the plain prompt passed every task of its kind both times. It hurt: it failed 2 tasks that the "
            "plain prompt passed both times.") in line


def test_a_stopped_make_is_made_again(setup):
    folder = Path(os.environ["BRIEFBENCH_HOME"]) / "bench" / "bench-t" / "demo-1" / "repos" / "half-made"
    folder.mkdir(parents=True)                     # a make stopped before the generator listed its tasks
    code, said = main(setup, "make")
    assert code == 0 and "has 6 tasks" in said and not folder.exists()


def test_a_trick_runs_from_a_copy_of_its_treatment_so_its_checkout_may_go(setup, tmp_path):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    assert main(setup, "run", "tip", "--yes", "--limit", "2")[0] == 0
    [name] = {e["experiment"] for e in entries() if e["kind"] == "run"}
    frozen = json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / f"{name}.json").read_text())
    copy = Path(frozen["b"]["path"])
    assert copy.parent.parent == Path(os.environ["BRIEFBENCH_HOME"]) / "bench" / "bench-t" / "treatments"
    moved = tmp_path / "elsewhere" / "tip.md"            # the checkout that froze it is gone; another has the same text
    moved.parent.mkdir()
    setup["tip"].rename(moved)
    tricks = json.loads(setup["tricks"].read_text())
    tricks["tricks"][0]["treatment"] = f"snippet:{moved}"
    setup["tricks"].write_text(json.dumps(tricks))
    code, said = main(setup, "run", "tip", "--yes")
    assert code == 0, said
    assert sum(e["kind"] == "run" and e["experiment"] == name for e in entries()) == 5


def test_runs_made_with_other_worker_settings_are_not_compared(setup):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    recipe = json.loads(setup["recipe"].read_text())
    recipe["timeout_minutes"] = 6
    setup["recipe"].write_text(json.dumps(recipe))
    code, said = main(setup, "run", "tip", "--yes")
    assert code == 2 and "another worker, model or time limit" in said and entries()[-1]["kind"] == "aa"
    recipe["timeout_minutes"] = 5
    setup["recipe"].write_text(json.dumps(recipe))
    assert main(setup, "run", "tip", "--yes")[0] == 0
    [name] = {e["experiment"] for e in entries() if e["kind"] == "run"}
    path = Path(os.environ["BRIEFBENCH_HOME"]) / "experiments" / f"{name}.json"
    frozen = json.loads(path.read_text())
    frozen["worker"]["argv"] = frozen["worker"]["argv"] + ["--another-flag"]      # a worker command since changed
    path.write_text(json.dumps(frozen))
    line = next(line for line in main(setup, "board")[1].splitlines() if line.startswith("| [tip]"))
    assert "Not comparable" in line and "3/3" not in line


def test_a_tricks_failed_runs_are_shown_and_a_task_that_failed_twice_is_left_out(setup, monkeypatch):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    monkeypatch.setenv("FAKE_WORKER", "limit")
    assert main(setup, "run", "tip", "--yes")[0] == 4
    line = next(line for line in main(setup, "board")[1].splitlines() if line.startswith("| [tip]"))
    assert "1 run failed once and waits for a retry." in line
    assert main(setup, "run", "tip", "--yes")[0] == 4                      # the retry fails too
    line = next(line for line in main(setup, "board")[1].splitlines() if line.startswith("| [tip]"))
    assert "1 task failed twice before a result (at the run step) and is left out." in line
    monkeypatch.setenv("FAKE_WORKER", "good")
    assert main(setup, "run", "tip", "--yes")[0] == 0
    assert sum(e["kind"] == "run" for e in entries()) == 4                 # the task left out isn't run again
    line = next(line for line in main(setup, "board")[1].splitlines() if line.startswith("| [tip]"))
    assert "runs so far" not in line and "left out" in line


@pytest.mark.parametrize("trick,words", [("later", "waits for its tasks, in another session"),
                                         ("nope", "No trick 'nope'")])
def test_a_trick_without_its_treatment_or_its_tasks_waits(setup, trick, words):
    assert main(setup, "make")[0] == 0
    code, said = main(setup, "run", trick, "--yes")
    assert code == 2 and words in said


def test_the_table_compares_each_trick_with_the_plain_prompts_two_runs(setup):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    assert main(setup, "run", "tip", "--yes")[0] == 0
    code, text = main(setup, "board", "--write")
    assert code == 0 and setup["board"].read_text() in text
    rows = {line.split(" | ")[0].lstrip("| "): line for line in text.splitlines() if line.startswith("| ")}
    header = next(line for line in text.splitlines() if line.startswith("| Trick | Its kinds"))
    assert text.splitlines()[text.splitlines().index(header) + 1] == "|---" * header.count(" | ") + "|---|"
    assert "| 0/6 | 4/4 | 0/2 |" in rows["The plain prompt, two runs per task"]
    tip = next(line for name, line in rows.items() if name.startswith("[tip]"))
    assert "| 3/3 (+3) | 0/2 (−2) | can't |" in tip
    assert "Worth a full test: on its kind of task it passed 3 that the plain prompt failed both times." in tip
    assert "It hurt: it failed 2 tasks that the plain prompt passed both times." in tip
    assert "No room: the plain prompt passed every task of its kind both times." in rows["[tip-down](../claims/tip-down.md)"]
    assert "| [later](../claims/later.md) | its tasks, in another session |" in text      # waiting
    assert "| More (`later/1:more`) | coding | — | not made yet |" in text
    assert "development data, not evidence" in text


def test_a_trick_that_ran_on_part_of_its_tasks_says_so(setup):
    assert main(setup, "make")[0] == 0 and main(setup, "plain", "--yes")[0] == 0
    assert main(setup, "run", "tip", "--yes", "--limit", "2")[0] == 0
    text = main(setup, "board")[1]
    assert "2 of 5 runs so far." in next(line for line in text.splitlines() if line.startswith("| [tip]"))


# ----------------------------------------------------------------------------- the repository's own bench

RECIPE, TRICKS = json.loads(bench.RECIPE.read_text()), json.loads(bench.TRICKS.read_text())


def test_every_claim_card_has_one_line_in_the_trick_list():
    cards = sorted(p.stem for p in (ROOT / "claims").glob("*.md") if p.stem != "README")
    ids = [t["id"] for t in TRICKS["tricks"]]
    assert sorted(ids) == cards and len(set(ids)) == len(ids)


def test_each_trick_names_a_treatment_that_is_there_and_kinds_the_recipe_has_or_says_what_it_waits_for():
    known = {k["id"] for k in bench.kinds(RECIPE)}
    for trick in TRICKS["tricks"]:
        assert set(trick["kinds"]) <= known, trick["id"]
        if trick["treatment"]:
            kind, _, where = trick["treatment"].partition(":")
            assert kind in ("snippet", "skill") and (ROOT / where).exists(), trick["id"]
            assert trick["kinds"], trick["id"]                 # its kinds of task are named before it runs
        else:
            assert trick.get("waits"), trick["id"]


def test_the_recipe_names_four_tasks_of_each_kind_from_generators_with_the_same_command_shape():
    seeds = [s["seed"] for s in RECIPE["sets"]]
    assert len(set(seeds)) == len(seeds) and RECIPE["name"] == "bench-1"
    assert RECIPE["worker"] == {"agent": "claude-code", "model": "claude-opus-5-5"}
    for s in RECIPE["sets"]:
        generator = ROOT / s["generator"]
        for k in s["kinds"]:
            assert k["tasks"] == 4 and k["flag"].startswith("--") and k["label"] and k["about"]
            if generator.exists():                              # a generator not merged yet waits
                assert f'"{k["flag"]}"' in generator.read_text() or f"'{k['flag']}'" in generator.read_text()

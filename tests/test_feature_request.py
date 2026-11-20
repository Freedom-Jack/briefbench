"""scripts/materials/feature_request.py: coding feature requests with decisions left out, for round 3 of the skill's
growth, offline. Every file is written under a temporary folder."""
import ast
import importlib.util
import json
import random
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from briefbench.tasks import load

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "materials" / "feature_request.py"
_spec = importlib.util.spec_from_file_location("feature_request", SCRIPT)
fr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fr)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """Twelve tasks, six of each kind, from all three kinds of feature: (task files, plans by id). The checks run on
    this interpreter."""
    folder = tmp_path_factory.mktemp("made")
    files = fr.make(seed=11, gap=6, complete=6, out=folder / "repos", keys=folder / "keys", python=sys.executable)
    return files, {t["name"]: t for t in (fr.plan(11, kind, k) for kind, k in fr.order(6, 6))}


def each(made):
    files, plans = made
    for path in files:
        task = load(path)
        yield path, task, plans[task["id"]]


def run_check(task: dict, cwd: Path):
    """The task file's check command, run as the bench runs it, in `cwd`."""
    return subprocess.run(shlex.split(task["check"]), cwd=cwd, capture_output=True, text=True)


def build(plan: dict, folder: Path, decisions=None, **style) -> Path:
    """A repo with a reference build of the feature: the task's decisions, or others, written in a given style."""
    return fr.write(folder, fr.files(plan, {**(decisions or plan["decisions"]), **style}))


def test_a_set_is_a_list_of_task_files_with_the_requesters_facts(made):
    files, plans = made
    keys = files[0].parent.parent
    assert (keys / "tasks.txt").read_text().split() == [str(f.relative_to(keys)) for f in files]
    found = json.loads((keys / "set.json").read_text())
    assert found["python"] == sys.executable and found["seed"] == 11
    assert {plans[load(f)["id"]]["feature"] for f in files} == set(fr.FEATURES)
    for path, task, plan in each(made):
        assert task["set"] == fr.SET and task["type"] == "code" and task["stratum"] == plan["kind"]
        assert task["generator_sha256"] == task["checker_sha256"] == found["generator_sha256"]
        assert shlex.split(task["check"])[:3] == [sys.executable, "-I", str(keys / "feature_request.py")]
        said = [text for _name, text in fr.sentences(plan["feature"], plan["decisions"])]
        assert all(s in task["facts"] for s in said) and fr.STANDING in task["facts"] and len(task["facts"]) == 7
        extra = [t for t in task["facts"] if t not in said and t != fr.STANDING]
        words = fr.FEATURE_TEXT[plan["feature"]]
        assert len([t for t in extra if t in words["context"]]) == 1 and len([t for t in extra if t in words["design"]]) == 1
        key = json.loads((path.parent / "key.json").read_text())
        assert key["decisions"] == json.loads(json.dumps(plan["decisions"]))
        assert [f["text"] for f in key["facts"]] == task["facts"]
        assert sorted(f["decision"] for f in key["facts"] if f["role"] == "decision") == sorted(key["sentences"])


def test_a_gap_request_leaves_every_decision_out_and_a_complete_one_states_them(made):
    for _path, task, plan in each(made):
        said = [text for _name, text in fr.sentences(plan["feature"], plan["decisions"])]
        interface = fr.FEATURE_TEXT[plan["feature"]]["interface"]
        assert interface in task["prompt"] and fr.FEATURE_TEXT[plan["feature"]]["file"] in task["prompt"]
        if plan["kind"] == "gap":
            assert fr.CUE in task["prompt"] and not any(s in task["prompt"] for s in said)
            numbers = {str(v) for v in plan["decisions"].values() if isinstance(v, int)}
            assert not any(f" {n} " in task["prompt"] for n in numbers - {"0", "1"})
        else:
            assert fr.CUE not in task["prompt"] and all(s in task["prompt"] for s in said)


def test_the_repo_never_depends_on_the_decisions(made):
    for _path, task, plan in each(made):
        repo = Path(task["repo"])
        committed = {p.relative_to(repo).as_posix(): p.read_text() for p in repo.rglob("*")
                     if p.is_file() and ".git" not in p.parts}
        assert committed == fr.files(plan)
        for other in (fr.decide(plan["feature"], random.Random(n)) for n in range(5)):
            assert fr.files({**plan, "decisions": other}) == committed


def test_the_visible_tests_pass_on_the_repo_and_on_a_reference_build(made, tmp_path):
    for n, (_path, task, plan) in enumerate(each(made)):
        for where in (Path(task["repo"]), build(plan, tmp_path / f"build-{n}")):
            done = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=where, capture_output=True, text=True)
            assert done.returncode == 0, done.stderr


def test_the_check_fails_the_repo_as_made_and_passes_a_reference_build(made, tmp_path):
    for n, (_path, task, plan) in enumerate(each(made)):
        made_check = run_check(task, Path(task["repo"]))
        assert made_check.returncode == 1 and "FAIL" in made_check.stdout
        reference = run_check(task, build(plan, tmp_path / f"ref-{n}"))
        assert reference.returncode == 0, reference.stdout
        assert reference.stdout.splitlines()[0].startswith("Python ") and "All " in reference.stdout


def test_every_task_needs_all_four_decisions_without_a_redraw(made):
    """make checks every task: the repo fails, the reference passes, and each build with one decision changed, the
    usual default numbers included, fails. Here no task needed its decisions drawn again."""
    for _path, _task, plan in each(made):
        assert plan["attempts"] == 1 and fr.problems(plan) == []
        assert len(fr.changes(plan)) >= 15


@pytest.mark.parametrize("seed", range(4))
def test_more_tasks_of_every_kind_need_all_four_decisions(seed):
    for kind, k in fr.order(3, 3):
        plan = fr.plan(100 + seed, kind, k)
        assert plan["attempts"] == 1, (plan["feature"], plan["decisions"])


def test_the_numbers_leave_out_the_usual_defaults():
    assert not set(fr.RL_N) & set(fr.WRONG["n"]) and not set(fr.RL_W) & set(fr.WRONG["w"])
    assert not set(fr.PG_SIZES) & set(fr.WRONG["size"]) and not set(fr.RT_TRIES) & set(fr.WRONG["tries"])
    assert not set(fr.RT_WAITS) & set(fr.WRONG["s"]) and min(fr.RT_TRIES) >= 4      # three waits at least


def first_of(made, feature: str) -> dict:
    return next(plan for _p, _t, plan in each(made) if plan["feature"] == feature)


@pytest.mark.parametrize("style", [{"style": "fixed"}, {"style": "first"}, {"round": "int+1"}, {"extra": True},
                                   {"count": True}, {"direct": True}, {"shared": True},
                                   {"style": "fixed", "round": "int+1", "extra": True}])
def test_faithful_rate_limiters_pass(made, tmp_path, style):
    """Every reasonable way of building the decided limit passes: fixed or sliding windows, a wait rounded up either
    way, extra headers, refused requests counted, time read straight from time.monotonic, counts kept in a module."""
    plan = first_of(made, "ratelimit")
    for n, (_name, decisions) in enumerate([("decided", plan["decisions"])] + [
            ("other", fr.decide("ratelimit", random.Random(s))) for s in range(6)]):
        other = {**plan, "decisions": decisions}
        assert fr.passes(fr.key_of(other), build(other, tmp_path / f"b{n}", **style)), (style, decisions)


def test_a_token_bucket_fails(made, tmp_path):
    """A token bucket lets more than N requests through in some span, which breaks "at most N in any span"."""
    plan = first_of(made, "ratelimit")
    passed, message = fr.run_case(fr.key_of(plan), "window", build(plan, tmp_path / "token", style="token"))
    assert not passed and "seconds later got status 200" in message


@pytest.mark.parametrize("style", [{"constant": True}, {"per_path": True}, {"list_only": True}])
def test_rate_limiters_that_break_a_decision_fail(made, tmp_path, style):
    """A Retry-After that always gives the whole span, a budget for each path, or a limit on the list alone all break
    what the requester decided, and each fails on every task that has the decision they break."""
    plan = first_of(made, "ratelimit")
    for n in range(12):
        other = {**plan, "decisions": fr.decide("ratelimit", random.Random(n))}
        if style.get("constant") and other["decisions"]["over"] == "429-bare":
            continue                                       # no Retry-After header to get wrong
        assert not fr.passes(fr.key_of(other), build(other, tmp_path / f"b{n}", **style)), (style, other["decisions"])


@pytest.mark.parametrize("style", [{"sorted_all": True}, {"subclass": True}])
def test_faithful_pages_pass(made, tmp_path, style):
    plan = first_of(made, "paging")
    for n in range(6):
        other = {**plan, "decisions": fr.decide("paging", random.Random(n))}
        other["probe"] = fr.probe("paging", other["decisions"], random.Random(n))
        assert fr.passes(fr.key_of(other), build(other, tmp_path / f"b{n}", **style)), (style, other["decisions"])


@pytest.mark.parametrize("style", [{"sleep": "module"}, {"power": True}, {"helper": True}, {"deadline": True}])
def test_faithful_retries_pass(made, tmp_path, style):
    """Waits through `from time import sleep`, a doubled wait worked out from the try's number, a helper added to the
    repo's own Response class, and waits that sleep until a deadline all pass too."""
    plan = first_of(made, "retry")
    for n in range(8):
        other = {**plan, "decisions": fr.decide("retry", random.Random(n))}
        other["probe"] = fr.probe("retry", other["decisions"], random.Random(n))
        assert fr.passes(fr.key_of(other), build(other, tmp_path / f"b{n}", **style)), (style, other["decisions"])


def test_a_check_line_says_what_went_wrong_in_plain_words(made, tmp_path):
    plan = first_of(made, "ratelimit")
    wrong = {**plan["decisions"], "n": plan["decisions"]["n"] + 1}
    passed, message = fr.run_case(fr.key_of(plan), "limit", build(plan, tmp_path / "wrong", decisions=wrong))
    assert not passed and message.startswith(f"request {plan['decisions']['n'] + 1} at once")
    assert "got status 200" in message


def test_code_that_doesnt_import_or_hangs_fails_with_a_plain_line(made, tmp_path, monkeypatch):
    path, task, plan = next(x for x in each(made) if x[2]["feature"] == "paging")
    broken = fr.write(tmp_path / "broken", {**fr.files(plan), "catalog/store.py": "def list(:\n"})
    passed, message = fr.child(path.parent / "key.json", "first page", broken)
    assert not passed and "the code doesn't import: SyntaxError in catalog/store.py, line 1" in message
    stuck = fr.write(tmp_path / "stuck", {**fr.files(plan), "catalog/store.py": "while True:\n    pass\n"})
    monkeypatch.setattr(fr, "CASE_SECONDS", 1)
    passed, message = fr.child(path.parent / "key.json", "first page", stuck)
    assert not passed and message == "it took more than 1 seconds"


def test_a_case_runs_on_a_copy_with_an_empty_home(made, tmp_path):
    """A build that writes files where it runs, or into its home folder, changes neither the arm's folder nor the next
    case."""
    path, task, plan = next(x for x in each(made) if x[2]["feature"] == "retry")
    code = fr.files(plan, plan["decisions"])["notify/sender.py"]
    code += ("\nimport os\nopen('written.txt', 'w').write('x')\n"
             "open(os.path.join(os.path.expanduser('~'), 'home.txt'), 'w').write('x')\n")
    root = fr.write(tmp_path / "writes", {**fr.files(plan), "notify/sender.py": code})
    assert fr.child(path.parent / "key.json", "success", root)[0]
    assert not (root / "written.txt").exists()


def test_a_link_in_the_arms_folder_is_copied_as_a_link(made, tmp_path):
    """A link the worker left behind, even one that leads nowhere, neither stops the check nor gets followed."""
    path, task, plan = next(x for x in each(made) if x[2]["feature"] == "paging")
    root = build(plan, tmp_path / "linked")
    (root / "cache").symlink_to(tmp_path / "nowhere")
    assert fr.child(path.parent / "key.json", "first page", root)[0]


def test_the_script_and_every_repo_file_are_python_3_9(made):
    ast.parse(SCRIPT.read_text(), feature_version=(3, 9))
    for _path, _task, plan in each(made):
        for name, text in {**fr.files(plan), **fr.files(plan, plan["decisions"])}.items():
            if name.endswith(".py"):
                ast.parse(text, feature_version=(3, 9))


@pytest.mark.skipif(not Path("/usr/bin/python3").is_file(), reason="no /usr/bin/python3 here")
def test_the_check_runs_on_the_systems_python3(made, tmp_path):
    path, task, plan = next(x for x in each(made) if x[2]["feature"] == "ratelimit")
    command = shlex.split(task["check"])
    done = subprocess.run(["/usr/bin/python3", *command[1:]], cwd=build(plan, tmp_path / "ref"), capture_output=True,
                          text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_worker_python_is_the_first_outside_the_checkout_and_any_virtualenv(tmp_path, monkeypatch):
    places = {name: tmp_path / name for name in ("checkout/.venv/bin", "venv/bin", "system/bin")}
    for place in places.values():
        place.mkdir(parents=True)
        (place / "python3").write_text("#!/bin/sh\n")
        (place / "python3").chmod(0o755)
    monkeypatch.setenv("PATH", ":".join(str(p) for p in places.values()))
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "venv"))
    assert fr.worker_python(tmp_path / "checkout") == str(places["system/bin"] / "python3")


def test_explain_gives_each_tasks_decisions_in_the_order_of_the_list(made):
    files, plans = made
    found = fr.explain(11, 6, 6)
    assert [x["id"] for x in found] == [load(f)["id"] for f in files]
    assert all(x["said"] == [t for _n, t in fr.sentences(x["feature"], x["decisions"])] for x in found)


def test_a_seed_gives_the_same_set_and_a_set_is_never_added_to(tmp_path):
    first = fr.make(seed=5, gap=1, complete=2, out=tmp_path / "r1", keys=tmp_path / "k1", python=sys.executable)
    second = fr.make(seed=5, gap=1, complete=2, out=tmp_path / "r2", keys=tmp_path / "k2", python=sys.executable)
    assert [load(f)["commit"] for f in first] == [load(f)["commit"] for f in second]
    assert [load(f)["prompt"] for f in first] == [load(f)["prompt"] for f in second]
    with pytest.raises(SystemExit):
        fr.make(seed=5, gap=1, complete=1, out=tmp_path / "r1", keys=tmp_path / "k3", python=sys.executable)
    with pytest.raises(SystemExit):
        fr.make(seed=5, gap=1, complete=1, out=tmp_path / "same", keys=tmp_path / "same" / "keys",
                python=sys.executable)

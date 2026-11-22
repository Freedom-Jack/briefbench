"""scripts/materials/failing_import.py: small CSV importers whose import stops on a file, for the pilot of Rieseberg's
advice to ask for the outcome, not the task, offline. Every file is written under a temporary folder."""
import ast
import datetime
import importlib.util
import json
import shlex
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from briefbench.tasks import load

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "materials" / "failing_import.py"
_spec = importlib.util.spec_from_file_location("failing_import", SCRIPT)
fi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fi)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """Twelve tasks, six of each kind, from all three kinds of export: (task files, plans by id). The checks run on
    this interpreter."""
    folder = tmp_path_factory.mktemp("made")
    files = fi.make(seed=11, more=6, only=6, out=folder / "repos", keys=folder / "keys", python=sys.executable)
    return files, {t["name"]: t for t in (fi.plan(11, kind, k) for kind, k in fi.order(6, 6))}


def each(made):
    files, plans = made
    for path in files:
        task = load(path)
        yield path, task, plans[task["id"]]


def run_check(task: dict, cwd: Path):
    """The task file's check command, run as the bench runs it, in `cwd`."""
    return subprocess.run(shlex.split(task["check"]), cwd=cwd, capture_output=True, text=True)


def reference(plan: dict, folder: Path) -> Path:
    """A repo whose importer fixes every kind of failure in the task's data/, each in its first style."""
    return fi.write(folder, fi.files(plan, fi.fix(fi.kinds_of(plan))))


def with_failure(failure: str, kind: str = "more") -> dict:
    """A task of one kind whose data/ holds a kind of failure, unchecked (make checks every task it writes)."""
    for k in range(60):
        plan = fi.plan(300, kind, k, verify=False)
        if failure in fi.kinds_of(plan):
            return plan
    raise AssertionError(f"no {kind} task with {failure}")


def test_a_set_is_a_list_of_task_files_with_the_requesters_facts(made):
    files, plans = made
    keys = files[0].parent.parent
    assert (keys / "tasks.txt").read_text().split() == [str(f.relative_to(keys)) for f in files]
    found = json.loads((keys / "set.json").read_text())
    assert found["python"] == sys.executable and found["seed"] == 11
    assert {plans[load(f)["id"]]["export"] for f in files} == set(fi.EXPORTS)
    for path, task, plan in each(made):
        assert task["set"] == fi.SET and task["type"] == "code" and task["stratum"] == plan["kind"]
        assert task["generator_sha256"] == task["checker_sha256"] == found["generator_sha256"]
        assert shlex.split(task["check"])[:3] == [sys.executable, "-I", str(keys / "failing_import.py")]
        assert sorted(task["facts"]) == sorted(fi.fact_texts(plan["export"]).values()) and fi.STANDING in task["facts"]
        key = json.loads((path.parent / "key.json").read_text())
        assert [f["text"] for f in key["facts"]] == task["facts"]
        assert sorted(f["role"] for f in key["facts"]) == sorted(fi.fact_texts(plan["export"]))
        assert key["failures"] == fi.kinds_of(plan) and len(key["failures"]) == (3 if plan["kind"] == "more" else 1)
        others = [fi.OTHER + fi.OUTCOME_CASE[f] for f in fi.FAILURES if f not in key["failures"]]
        assert key["cases"] == (["ordinary rows"] + [fi.OUTCOME_CASE[f] for f in key["failures"]]
                                + list(fi.SCOPE_CASES) + others)
        assert {key["hidden"][c]["must"] for c in others} <= {"either"} and len(others) == 5 - len(key["failures"])


def test_the_two_kinds_differ_only_in_the_files_that_stop(made):
    """With the same names, a `more` task and the `only` task it would be without its two other kinds have the same
    code, README, tests, code list, request and facts: their data/ differs only in the files of those two kinds."""
    seen = 0
    for _path, task, plan in each(made):
        if plan["kind"] != "more":
            continue
        alone = {**plan, "kind": "only", "failures": [f for f in plan["failures"] if f["role"] != "more"]}
        mine, other = fi.files(plan), fi.files(alone)
        assert mine.keys() == other.keys()
        extra = {f"data/{plan['names']['files'][f['file']]['day']}.csv" for f in plan["failures"] if f["role"] == "more"}
        assert {p for p in mine if mine[p] != other[p]} == extra and len(extra) == 2
        assert fi.prompt(alone) == task["prompt"] and fi.facts(alone) == task["facts"]
        seen += 1
    assert seen == 6


def test_the_outcome_reaches_an_arm_only_through_the_facts(made):
    for _path, task, plan in each(made):
        outcome = fi.fact_texts(plan["export"])["outcome"]
        assert outcome in task["facts"]
        visible = [task["prompt"], *fi.files(plan).values()]
        assert not any(outcome in text or "every file" in text for text in visible)


def test_each_file_in_data_stops_as_planned_and_the_request_quotes_the_first(made):
    for _path, task, plan in each(made):
        repo = Path(task["repo"])
        for index, day in enumerate(plan["names"]["files"]):
            want = fi.planned_stop(plan, index)
            assert fi.run_import(repo, day["day"], plan["export"], sys.executable) == ((0, "") if want is None
                                                                                     else (1, want))
        first = fi.reported(plan)
        day = plan["names"]["files"][first["file"]]["day"]
        assert task["prompt"] == (f"Running `python3 -m {plan['export']} import data/{day}.csv` stops with "
                                  f"`{fi.planned_stop(plan, first['file'])}`. Please fix it.")
        stopping = [i for i in range(fi.DAYS) if fi.planned_stop(plan, i)]
        assert stopping[0] == first["file"] >= 2
        assert len(stopping) == len(plan["failures"])


def test_the_exports_hold_a_refund_and_an_amount_of_0(made):
    for _path, _task, plan in each(made):
        amounts = [row[2] for export in plan["names"]["files"] for row in export["rows"]]
        assert "0.00" in amounts and any(a.startswith("-") for a in amounts)


def test_the_visible_tests_pass_on_the_repo_and_on_a_reference_fix(made, tmp_path):
    for n, (_path, task, plan) in enumerate(each(made)):
        for where in (Path(task["repo"]), reference(plan, tmp_path / f"fix-{n}")):
            done = subprocess.run([sys.executable, "-B", "-m", "unittest", "-q"], cwd=where, capture_output=True,
                                  text=True)
            assert done.returncode == 0, done.stderr


def test_the_check_fails_the_repo_as_made_only_on_the_outcome_and_passes_a_reference_fix(made, tmp_path):
    for n, (_path, task, plan) in enumerate(each(made)):
        made_check = run_check(task, Path(task["repo"]))
        failed = [line for line in made_check.stdout.splitlines() if line.startswith("FAIL")]
        assert made_check.returncode == 1 and len(failed) == len(fi.kinds_of(plan))
        assert all(line.startswith("FAIL  outcome: ") for line in failed)
        fixed = run_check(task, reference(plan, tmp_path / f"ref-{n}"))
        assert fixed.returncode == 0, fixed.stdout
        assert fixed.stdout.splitlines()[0].startswith("Python ") and "All " in fixed.stdout


def test_fixing_only_the_reported_kind_fails_a_more_task_and_passes_an_only_one(made, tmp_path):
    for n, (_path, task, plan) in enumerate(each(made)):
        literal = fi.write(tmp_path / f"literal-{n}", fi.files(plan, fi.fix([fi.reported(plan)["kind"]])))
        result = run_check(task, literal)
        assert (result.returncode == 0) == (plan["kind"] == "only"), result.stdout
        failed = [line for line in result.stdout.splitlines() if line.startswith("FAIL")]
        assert len(failed) == (2 if plan["kind"] == "more" else 0)
        assert all(line.startswith("FAIL  outcome: ") for line in failed)


def test_every_task_is_fair_without_a_redraw(made):
    """make checks every task (`problems`); here no task needed its failures drawn again."""
    for _path, _task, plan in each(made):
        assert plan["attempts"] == 1 and fi.problems(plan) == []


@pytest.mark.parametrize("seed", range(3))
def test_more_tasks_of_both_kinds_are_fair_without_a_redraw(seed):
    for kind, k in fi.order(2, 2):
        assert fi.plan(100 + seed, kind, k)["attempts"] == 1


@pytest.mark.parametrize("failure", fi.FAILURES)
def test_every_style_of_fix_passes(failure, tmp_path):
    """Each kind of failure fixed in each of its styles passes, with the task's other kinds fixed in their first:
    replacing the separators, matching them first, or through Decimal; a date's first ten characters, its first word or
    fromisoformat; utf-8-sig, the mark taken off the field names or off the text; a code stripped on both sides, on the
    right, or by a regex; an empty text kept as it is or as None."""
    plan = with_failure(failure)
    for n, style in enumerate(fi.STYLES[failure]):
        build = fi.fix(fi.kinds_of(plan))
        build["fix"][failure] = style
        root = fi.write(tmp_path / f"b{n}", fi.files(plan, build))
        failing = [(c, m) for c in fi.cases(fi.key_of(plan)) for ok, m in [fi.run_case(fi.key_of(plan), c, root)]
                   if not ok]
        assert not failing, (style, failing)


OVER_REACH = [
    ("skip", "no code"), ("zero", "amount n/a"), ("pattern_date", "date 30 February"), ("rename", "ordinary rows"),
    ("no_refund", "refunds and 0"), ("pad_list", "data unchanged"), ("edit_data", "data unchanged"),
    ("decimal_raw", "the command"), ("string_amount", "ordinary rows"), ("lenient_main", "the command"),
    ("drop_empty", "empty texts"), ("empty_zero", "amount empty"), ("write_back", "a byte-order mark"),
    ("lookup", "padded codes"), ("pattern_time", "date 30 February with a time")]


@pytest.mark.parametrize("harm, case, shown", [(harm, case, shown) for harm, case in OVER_REACH for shown in (True, False)
                                               if shown or harm != "pad_list"])      # pad_list needs padded codes
def test_fixes_that_over_reach_fail_where_they_over_reach(harm, case, shown, tmp_path):
    """Each fix that over-reaches fails, though every kind of failure in data/ is fixed, in a task whose data/ shows
    the kind it touches and in one whose data/ doesn't (there the case is the kind's "other kind" case): skipping rows
    that stop; reading a non-number or an empty amount as 0; checking a date, or a date with a time, by its pattern
    alone; renaming an entry's fields; refusing refunds; adding the padded codes to the code list, or keeping their
    padding; editing data/, or taking a byte-order mark off the file being read; amounts as Decimals the command can't
    add, or as text; a command that carries on past a wrong row; dropping rows with an empty text."""
    kind = {"empty texts": "empty", "a byte-order mark": "bom", "padded codes": "padded"}.get(case)
    plan = with_failure(kind or "padded") if shown else next(
        p for p in (fi.plan(300, "only", k, verify=False) for k in range(60)) if (kind or "padded") not in fi.kinds_of(p))
    key = fi.key_of(plan)
    root = fi.write(tmp_path / harm, fi.files(plan, fi.harmful(plan, harm)))
    name = case if (shown or not kind) else fi.OTHER + case
    passed, message = fi.run_case(key, name, root)
    assert not passed, message
    assert not fi.passes(key, root)


def test_a_check_line_says_what_went_wrong_in_plain_words(tmp_path):
    plan = with_failure("thousands")
    key = fi.key_of(plan)
    passed, message = fi.run_case(key, "thousands separators", fi.write(tmp_path / "made", fi.files(plan)))
    assert not passed and message.startswith("a file with thousands separators raised BadRowError: line ")
    assert message.endswith("is not a number")
    line = key["hidden"]["amount n/a"]["line"]
    passed, message = fi.run_case(key, "amount n/a", fi.write(tmp_path / "skip", fi.files(plan, fi.harmful(plan, "skip"))))
    assert not passed and message == f"a row whose amount is 'n/a', at line {line}, imported instead of stopping the import"


def test_rows_compare_as_a_set_with_room_for_reasonable_types():
    """A date object, or a date that keeps its time; an amount as a float, int or Decimal within half a cent; a trimmed
    text, or none where the file's is empty; an entry as an object; extra fields. Not an amount as text, which the
    README rules out, nor a code with its padding, which isn't in the list."""
    fields = {"date": "date", "code": "account", "amount": "amount", "text": "memo"}
    want = [["2026-11-02", "ACC-104", "1250.00", "Rent"], ["2026-11-02", "ACC-210", "-12.40", ""]]

    class Entry:
        def __init__(self, **values):
            self.__dict__.update(values)

    got = [Entry(date=datetime.date(2026, 11, 2), account="ACC-210", amount=Decimal("-12.4"), memo=None),
           {"date": "2026-11-02 09:30:00", "account": "ACC-104", "amount": 1250.004, "memo": " Rent ", "extra": 1}]
    assert fi.same_rows(got, want, fields) is None
    assert fi.same_rows([got[0], {**got[1], "amount": 1250}], want, fields) is None
    assert fi.same_rows(got[:1], want, fields) == "load gave 1 rows; the file has 2"
    for wrong in ({"amount": 1250.01}, {"amount": "1250.00"}, {"amount": "1,250.00"}, {"amount": True},
                  {"memo": "Rent!"}, {"memo": None}, {"account": "ACC-105"}, {"account": "ACC-104  "},
                  {"date": "2026-11-03"}):
        changed = [got[0], {**got[1], **wrong}]
        assert fi.same_rows(changed, want, fields).startswith("load gave a row that doesn't match the file: ")


def test_a_line_is_named_as_a_whole_number_or_an_attribute_never_by_a_path():
    error = Exception("line 12: no account")
    assert fi.names_line(error, 12) and not fi.names_line(error, 2) and not fi.names_line(Exception("line 112"), 12)
    named = Exception("no account")
    named.line = 7
    assert fi.names_line(named, 7)
    assert not fi.names_line(Exception("/tmp/import-case-k3_x/2026-11-20.csv: no account"), 3)
    assert fi.names_line(Exception("/tmp/import-case-k3_x/2026-11-20.csv, line 4: amount 'n/a' is not a number"), 4)


def test_the_command_case_passes_as_made_and_catches_a_command_that_breaks_or_carries_on(tmp_path):
    plan = with_failure("thousands")
    key = fi.key_of(plan)
    assert fi.run_case(key, "the command", fi.write(tmp_path / "made", fi.files(plan)))[0]
    passed, message = fi.run_case(key, "the command", fi.write(tmp_path / "lenient", fi.files(
        plan, fi.harmful(plan, "lenient_main"))))
    assert not passed and "carried on past a row with no " in message and "exited 0" in message
    passed, message = fi.run_case(key, "the command", fi.write(tmp_path / "decimal", fi.files(
        plan, fi.harmful(plan, "decimal_raw"))))
    assert not passed and "failed on a file of ordinary rows: TypeError" in message


def test_a_kind_data_doesnt_show_may_stop_the_import_but_not_import_wrong(tmp_path):
    plan = next(p for p in (fi.plan(300, "only", k, verify=False) for k in range(60)) if "empty" not in fi.kinds_of(p))
    key, case = fi.key_of(plan), fi.OTHER + fi.OUTCOME_CASE["empty"]
    passed, message = fi.run_case(key, case, fi.write(tmp_path / "made", fi.files(plan)))
    assert passed and "a kind data/ doesn't show, stops the import: BadRowError" in message
    assert fi.run_case(key, case, fi.write(tmp_path / "all", fi.files(plan, fi.fix(fi.FAILURES))))[0]
    passed, message = fi.run_case(key, case, fi.write(tmp_path / "drop", fi.files(plan, fi.harmful(plan, "drop_empty"))))
    assert not passed and "load gave 4 rows; the file has 7" in message


def test_code_that_doesnt_import_or_hangs_fails_with_a_plain_line(made, tmp_path, monkeypatch):
    path, _task, plan = next(each(made))
    module = f"{plan['export']}/importer.py"
    broken = fi.write(tmp_path / "broken", {**fi.files(plan), module: "def load(:\n"})
    passed, message = fi.child(path.parent / "key.json", "ordinary rows", broken)
    assert not passed and f"the code doesn't import: SyntaxError in {module}, line 1" in message
    stuck = fi.write(tmp_path / "stuck", {**fi.files(plan), module: "while True:\n    pass\n"})
    monkeypatch.setattr(fi, "CASE_SECONDS", 1)
    passed, message = fi.child(path.parent / "key.json", "ordinary rows", stuck)
    assert not passed and message == "it took more than 1 seconds"


def test_a_case_runs_on_a_copy_with_an_empty_home(made, tmp_path):
    """A build that writes files where it runs, or into its home folder, changes neither the arm's folder nor the next
    case."""
    path, _task, plan = next(each(made))
    module = f"{plan['export']}/importer.py"
    code = fi.files(plan, fi.fix(fi.kinds_of(plan)))[module]
    code += ("\nimport os\nopen('written.txt', 'w').write('x')\n"
             "open(os.path.join(os.path.expanduser('~'), 'home.txt'), 'w').write('x')\n")
    root = fi.write(tmp_path / "writes", {**fi.files(plan), module: code})
    assert fi.child(path.parent / "key.json", "ordinary rows", root)[0]
    assert not (root / "written.txt").exists()


def test_a_link_in_the_arms_folder_is_copied_as_a_link(made, tmp_path):
    path, _task, plan = next(each(made))
    root = reference(plan, tmp_path / "linked")
    (root / "cache").symlink_to(tmp_path / "nowhere")
    assert fi.child(path.parent / "key.json", "ordinary rows", root)[0]


def test_a_data_file_replaced_by_a_link_counts_as_changed(made, tmp_path):
    _path, _task, plan = next(each(made))
    root = reference(plan, tmp_path / "relinked")
    first = root / f"data/{plan['names']['files'][0]['day']}.csv"
    copy = tmp_path / "copy.csv"
    copy.write_bytes(first.read_bytes())
    first.unlink()
    first.symlink_to(copy)
    passed, message = fi.run_case(fi.key_of(plan), "data unchanged", root)
    assert not passed and first.relative_to(root).as_posix() in message


def test_the_repos_tests_run_as_committed_even_when_an_arm_rewrote_them(made, tmp_path):
    _path, _task, plan = next(each(made))
    files = fi.files(plan, fi.harmful(plan, "skip"))
    files["tests/test_importer.py"] = "import unittest\n"
    root = fi.write(tmp_path / "rewritten", files)
    passed, message = fi.run_case(fi.key_of(plan), "the repo's tests", root)
    assert not passed and "of the repo's 6 tests, as committed, fail" in message


def test_the_script_and_every_repo_file_are_python_3_9(made):
    ast.parse(SCRIPT.read_text(), feature_version=(3, 9))
    for _path, _task, plan in each(made):
        builds = [None] + [fi.fix(fi.FAILURES, n) for n in range(3)] + [fi.harmful(plan, h) for h in fi.HARMFUL]
        for build in builds:
            for name, text in fi.files(plan, build).items():
                if name.endswith(".py"):
                    ast.parse(text, feature_version=(3, 9))


@pytest.mark.skipif(not Path("/usr/bin/python3").is_file(), reason="no /usr/bin/python3 here")
def test_the_check_runs_on_the_systems_python3(made, tmp_path):
    _path, task, plan = next(each(made))
    command = shlex.split(task["check"])
    done = subprocess.run(["/usr/bin/python3", *command[1:]], cwd=reference(plan, tmp_path / "ref"),
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_worker_python_is_the_first_outside_the_checkout_and_any_virtualenv(tmp_path, monkeypatch):
    places = {name: tmp_path / name for name in ("checkout/.venv/bin", "venv/bin", "system/bin")}
    for place in places.values():
        place.mkdir(parents=True)
        (place / "python3").write_text("#!/bin/sh\n")
        (place / "python3").chmod(0o755)
    monkeypatch.setenv("PATH", ":".join(str(p) for p in places.values()))
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "venv"))
    assert fi.worker_python(tmp_path / "checkout") == str(places["system/bin"] / "python3")


def test_explain_gives_each_tasks_failures_in_the_order_of_the_list(made):
    files, _plans = made
    found = fi.explain(11, 6, 6)
    assert [x["id"] for x in found] == [load(f)["id"] for f in files]
    for x, path in zip(found, files):
        assert [d["role"] for d in x["data"]].count("reported") == 1
        assert x["request"]["stops_with"] in load(path)["prompt"]


def test_a_seed_gives_the_same_set_and_a_set_is_never_added_to(tmp_path):
    first = fi.make(seed=5, more=1, only=2, out=tmp_path / "r1", keys=tmp_path / "k1", python=sys.executable)
    second = fi.make(seed=5, more=1, only=2, out=tmp_path / "r2", keys=tmp_path / "k2", python=sys.executable)
    assert [load(f)["commit"] for f in first] == [load(f)["commit"] for f in second]
    assert [load(f)["prompt"] for f in first] == [load(f)["prompt"] for f in second]
    with pytest.raises(SystemExit):
        fi.make(seed=5, more=1, only=1, out=tmp_path / "r1", keys=tmp_path / "k3", python=sys.executable)
    with pytest.raises(SystemExit):
        fi.make(seed=5, more=1, only=1, out=tmp_path / "same", keys=tmp_path / "same" / "keys", python=sys.executable)

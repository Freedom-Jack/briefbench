"""New-bank coverage, independent repair checks and human-evaluation gates; all offline."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from briefbench import cli, tasks
from briefbench.errors import UsageError

ROOT = Path(__file__).resolve().parents[1]


def script(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


integration = script("integration_state_materials", "scripts/materials/integration_state.py")
evidence = script("evidence_synthesis_materials", "scripts/materials/evidence_synthesis.py")
bench = script("coverage_bench", "scripts/bench.py")
runner = script("coverage_runner", "scripts/run_tasks.py")


@pytest.fixture
def integration_tasks(tmp_path):
    return [tasks.load(p) for p in integration.make(23, 1, 1, tmp_path / "repos", tmp_path / "keys")]


@pytest.fixture
def human_task(tmp_path):
    return tasks.load(evidence.make(23, 0, 1, tmp_path / "repos", tmp_path / "keys")[0])


def test_new_recipe_preserves_existing_tasks_and_easy_sentinel_selection():
    old = bench.read(ROOT / "bench/bench-2-codex.json")
    new = bench.read(ROOT / "bench/bench-3-codex.json")
    assert new["name"] != old["name"] and new["sets"][:4] == old["sets"]
    assert new["worker"] == old["worker"] and new["timeout_minutes"] == old["timeout_minutes"]
    assert sum(k["tasks"] for s in new["sets"] for k in s["kinds"]) == 48
    def bank(recipe):
        return [{"set": s["set"], "stratum": k["name"], "id": f"{s['set']}-{k['name']}-{i}"}
                for s in recipe["sets"] for k in s["kinds"] for i in range(k["tasks"])]
    for trick in bench.read(ROOT / "bench/tricks.json")["tricks"]:
        if treatment := bench.treatment_of(trick):
            before = bench.selected(old, trick, treatment, bank(old))
            after = bench.selected(new, trick, treatment, bank(new))
            assert before == after
    # New coding families also receive the original complete-request sentinels.
    scope = bench.selected(new, {"kinds": ["integration-state/1:accounting"]},
                           {"kind": "snippet"}, list(reversed(bank(new))))
    assert len(scope) == 10
    assert all(t["set"] in ("integration-state/1", "failing-import/1", "feature-request/1") for t in scope)
    assert not any(t["stratum"] == "gap" for t in scope)


def test_integration_starter_fails_reference_passes_and_input_damage_fails(integration_tasks):
    for task in integration_tasks:
        repo = Path(task["repo"])
        key = Path(task["file"]).with_name("key.json")
        assert integration.check(key, repo) != 0
        original_inputs = {p: p.read_bytes() for p in (repo / "fixtures").iterdir()}
        for name, text in integration.files(task["stratum"], reference=True).items():
            (repo / name).write_text(text)
        assert integration.check(key, repo) == 0
        assert {p: p.read_bytes() for p in original_inputs} == original_inputs
        next(iter(original_inputs)).write_text("{}\n")
        assert integration.check(key, repo) != 0


@pytest.mark.parametrize("kind", ["accounting", "resume"])
def test_generator_checks_references_and_mutations_on_a_second_seed(tmp_path, kind):
    made = integration.make(104729, int(kind == "accounting"), int(kind == "resume"),
                            tmp_path / "repos", tmp_path / "keys")
    task = tasks.load(made[0])
    assert task["evaluation"] == "check" and not task["facts"]
    assert not Path(task["file"]).is_relative_to(task["repo"])
    assert "key.json" not in {p.name for p in Path(task["repo"]).rglob("*")}


@pytest.mark.parametrize("kind", ["complete", "incomplete"])
def test_evidence_has_consistent_denominators_and_a_non_prescriptive_human_rubric(tmp_path, kind):
    made = evidence.make(23, int(kind == "complete"), int(kind == "incomplete"),
                         tmp_path / "repos", tmp_path / "keys")
    task = tasks.load(made[0])
    rubric = json.loads(Path(task["rubric"]).read_text())
    assert task["evaluation"] == "human" and task["facts"] == []
    assert rubric["automatic_quality_verdict"] is None
    assert "judgment" in rubric["dimensions"] and "scope_fidelity" in rubric["dimensions"]
    assert not Path(task["rubric"]).is_relative_to(task["repo"])
    assert all((Path(task["repo"]) / p).is_file() for p in task["protected"])
    repo = Path(task["repo"])
    rows = list(csv.DictReader(io.StringIO((repo / "sources/04-results.csv").read_text())))
    baseline, pilot = ({k: int(v) if k != "workflow" else v for k, v in row.items()} for row in rows)
    assert baseline["jobs"] == pilot["jobs"] == baseline["correct_final"] == pilot["correct_final"]
    assert baseline["first_attempt_failures"] == 0 < pilot["first_attempt_failures"]
    assert (pilot["measured_jobs"] == pilot["jobs"]) == (kind == "complete")
    observations = (repo / "sources/05-metering.md").read_text()
    assert f"{pilot['measured_jobs']} measured, {pilot['known_units']} known units" in observations
    outcome_audit = (repo / "sources/03-operations.md").read_text()
    assert f"{pilot['first_attempt_failures']} had a failed first attempt" in outcome_audit
    if kind == "incomplete":
        assert any("unknown" in fact and "full total/average" in fact for fact in rubric["facts_to_verify"])
    else:
        assert any("observed pilot total is complete" in fact for fact in rubric["facts_to_verify"])
    report = Path(task["repo"]) / "report.md"
    report.write_text("A polished report with citations and all requested headings.")
    done = subprocess.run([sys.executable, "-I", str(Path(task["file"]).parent.parent / "evidence_synthesis.py"),
                           "check"], cwd=task["repo"], capture_output=True, text=True)
    assert done.returncode == 2 and "Human review required" in done.stderr


def test_generation_is_deterministic_and_source_variation_is_not_a_holdout():
    assert evidence.packet(23, "complete", 0) == evidence.packet(23, "complete", 0)
    assert evidence.packet(23, "complete", 0) != evidence.packet(24, "complete", 0)
    assert evidence.packet(23, "complete", 0) != evidence.packet(23, "incomplete", 0)


@pytest.mark.parametrize("family", ["integration", "synthesis"])
def test_saved_checks_outlive_the_environment_that_generated_them(tmp_path, monkeypatch, family):
    interpreter = tmp_path / "removed-environment" / "python"
    interpreter.parent.mkdir()
    interpreter.symlink_to(Path(sys.executable).resolve())
    with monkeypatch.context() as patch:
        patch.setattr(sys, "executable", str(interpreter))
        generator = integration if family == "integration" else evidence
        task = tasks.load(generator.make(23, 1, 0, tmp_path / "repos", tmp_path / "keys")[0])
    interpreter.unlink()
    if family == "integration":
        for name, text in integration.files("accounting", reference=True).items():
            (Path(task["repo"]) / name).write_text(text)
    done = subprocess.run(shlex.split(task["check"]), cwd=task["repo"], capture_output=True, text=True)
    assert done.returncode == (0 if family == "integration" else 2), done.stdout + done.stderr


def test_complete_bank_can_be_made_and_inspected_without_model_calls(tmp_path, monkeypatch):
    recipe = bench.read(ROOT / "bench/bench-3-codex.json")
    monkeypatch.setattr(cli, "_ready", lambda *_: pytest.fail("material generation must not discover agents"))
    with contextlib.redirect_stdout(io.StringIO()):
        assert bench.make(recipe) == 0
        assert bench.make(recipe) == 0     # frozen material identity remains reusable
    made = bench.bench_tasks(recipe)
    assert len(made) == 48
    assert sum(t["evaluation"] == "human" for t in made) == 8
    assert len({t["sha256"] for t in made}) == 48
    board = bench.board(recipe, bench.read(ROOT / "bench/tricks.json"))
    assert "human review required" in board and "Screen 0/10 completed" in board
    assert "known_tokens" not in board  # no outcomes have been invented from reference builds
    with contextlib.redirect_stderr(io.StringIO()) as err:
        assert bench.main(["--bench", str(ROOT / "bench/bench-3-codex.json"), "run", "ask-questions-first",
                           "--full", "--yes"]) == 2
    assert "Human review required" in err.getvalue()


@pytest.mark.parametrize("change", ["unknown-evaluation", "missing-rubric", "leaked-rubric"])
def test_human_evaluation_metadata_fails_closed(human_task, change):
    path = Path(human_task["file"])
    raw = json.loads(path.read_text())
    if change == "unknown-evaluation":
        raw["evaluation"] = "automatic-keywords"
    elif change == "missing-rubric":
        raw.pop("rubric")
    else:
        leaked = Path(human_task["repo"]) / "rubric.json"
        leaked.write_text(Path(human_task["rubric"]).read_text())
        raw["rubric"] = str(leaked)
    path.write_text(json.dumps(raw))
    with pytest.raises(UsageError):
        tasks.load(path)


def test_human_tasks_cannot_enter_automatic_execution_or_calibration(human_task, monkeypatch):
    path = Path(human_task["file"])
    exp = {"name": "no-execution", "scoring": "check", "a": {"kind": "original"}, "b": {"kind": "original"}}
    monkeypatch.setattr(cli.experiment, "load", lambda *_: exp)
    monkeypatch.setattr(cli.treatments, "check_unchanged", lambda *_: None)
    monkeypatch.setattr(cli, "_ready", lambda *_: pytest.fail("must reject before CLI discovery"))
    out, err = io.StringIO(), io.StringIO()
    assert cli.run(["ab", "--task", str(path), "--experiment", exp["name"]],
                   stdin=io.StringIO(""), stdout=out, stderr=err) == 2
    assert "Human review required" in err.getvalue()
    with pytest.raises(UsageError, match="Human review required"):
        tasks.freeze(path.parent.parent / "tasks.txt")
    with pytest.raises(UsageError, match="Human review required"):
        runner.main(["--experiment", exp["name"], str(path.parent.parent / "tasks.txt")])


def test_full_bank_and_human_screens_refuse_before_spending(human_task, monkeypatch):
    recipe = bench.read(ROOT / "bench/bench-3-codex.json")
    monkeypatch.setattr(bench, "bench_tasks", lambda *_: [human_task])
    monkeypatch.setattr(bench, "current_worker", lambda *_: pytest.fail("must reject before CLI discovery"))
    monkeypatch.setattr(bench, "agreed", lambda *_: pytest.fail("must reject before asking to spend"))
    monkeypatch.setattr(bench, "baseline", lambda *_: pytest.fail("must reject before looking for controls"))
    paths = {"recipe": ROOT / "bench/bench-3-codex.json"}
    with contextlib.redirect_stderr(io.StringIO()) as err:
        assert bench.main(["--bench", str(paths["recipe"]), "plain", "--full", "--yes"]) == 2
    assert "Human review required" in err.getvalue()
    monkeypatch.setattr(bench, "treatment_of", lambda *_: {"kind": "snippet"})
    trick = {"id": "fake", "kinds": ["evidence-synthesis/1:incomplete"]}
    args = type("Args", (), {"trick": "fake", "full": False})()
    with pytest.raises(UsageError, match="Human review required"):
        bench.run(recipe, {"tricks": [trick]}, args)


def test_new_board_writes_to_its_own_file_without_replacing_history(tmp_path, monkeypatch):
    recipe = bench.read(ROOT / "bench/bench-3-codex.json")
    for filename in ("bench-3-codex.json", "bench-2-codex.json", "tricks.json"):
        source = ROOT / "bench" / filename
        target = tmp_path / "bench" / filename
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(source.read_bytes())
    historical = tmp_path / "bench/board-2-codex.md"
    historical.write_text("historical results\n")
    monkeypatch.setattr(bench, "ROOT", tmp_path)
    monkeypatch.setattr(bench, "TRICKS", tmp_path / "bench/tricks.json")
    monkeypatch.setattr(bench, "board", lambda *_: "new bank, no results\n")
    with contextlib.redirect_stdout(io.StringIO()):
        assert bench.main(["--bench", str(tmp_path / "bench/bench-3-codex.json"), "board", "--write"]) == 0
    assert historical.read_text() == "historical results\n"
    assert (tmp_path / "bench/board-3-codex.md").read_text() == "new bank, no results\n"

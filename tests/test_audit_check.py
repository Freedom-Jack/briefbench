"""scripts/audit_check.py: your labels of calibration reports, compared with the check, offline."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("audit_check", ROOT / "scripts" / "audit_check.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def diff(report):
    """An arm's diff as the bench saves it, with report.md as a new file."""
    body = "".join(f"+{line}\n" for line in report.splitlines())
    return ("diff --git a/notes.txt b/notes.txt\nnew file mode 100644\n--- /dev/null\n+++ b/notes.txt\n@@ -0,0 +1 @@\n"
            "+scratch\n"
            f"diff --git a/report.md b/report.md\nnew file mode 100644\n--- /dev/null\n+++ b/report.md\n"
            f"@@ -0,0 +1,{len(report.splitlines())} @@\n{body}")


@pytest.fixture
def calibration(tmp_path):
    """A calibration experiment with two noise checks: four reports, each with the check's verdict, and the answers."""
    home = Path(os.environ["BRIEFBENCH_HOME"])
    (home / "experiments").mkdir(parents=True)
    (home / "experiments" / "cal.json").write_text(json.dumps({"format": 1, "name": "cal", "created": "c"}))
    lines = []
    for n, (task, passed, said) in enumerate([("t1", (True, False), ("payment_status", "plan")),
                                              ("t2", (True, True), ("weather", "storms"))]):
        out = tmp_path / f"trial{n}"
        out.mkdir()
        for side, words in zip("ab", said):
            (out / f"{side}.diff").write_text(diff(f"# Findings\n\nMain driver: {words}"))
        lines.append({"kind": "aa", "id": f"trial-{n}", "experiment": "cal", "experiment_created": "c",
                      "output": str(out), "task": {"source": {"id": task}},
                      "arms": {s: {"check": {"passed": p}} for s, p in zip("ab", passed)}})
    (home / "log.jsonl").write_text("".join(json.dumps(e) + "\n" for e in lines))
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps([{"id": "t1", "driver": "payment_status"}, {"id": "t2", "driver": "weather"}]))
    return answers


def run(answers, typed, *extra):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = audit.main(["--experiment", "cal", "--answers", str(answers), "--seed", "1", *extra],
                          stdin=io.StringIO(typed))
    return code, out.getvalue()


def test_the_report_is_read_from_the_arms_diff():
    assert audit.report_in(Path("/nowhere.diff"), "report.md") is None


def test_the_reports_are_shown_without_their_arm_or_verdict_and_compared(calibration):
    """You label four reports; the check passed t2's "storms", which you say doesn't name the answer, weather."""
    code, text = run(calibration, "maybe\ny\nn\ny\ny\n")      # a word that isn't y or n is asked again
    shown = text.split("The check agreed")[0]
    assert code == 0 and shown.count("The planted answer:") == 4 and "Main driver:" in shown
    assert "passed" not in shown and "trial-" not in shown and "arm" not in shown.lower()
    assert "scratch" not in shown                                 # only report.md, not the arm's other files
    saved = json.loads((Path(os.environ["BRIEFBENCH_HOME"]) / "audits" / "cal.json").read_text())
    labels = {(lab["task"], lab["side"]): lab for lab in saved["labels"]}
    assert len(labels) == 4 and all(set(lab) == {"trial", "side", "task", "passed", "names_answer"}
                                    for lab in labels.values())
    agreed = sum(lab["names_answer"] == lab["passed"] for lab in labels.values())
    assert f"The check agreed with your labels on {agreed} of 4 reports." in text
    assert text.count("check passed it") + text.count("check failed it") == 4 - agreed


def test_a_label_left_unanswered_saves_nothing(calibration):
    code, _ = run(calibration, "y\n")
    assert code == 130 and not (Path(os.environ["BRIEFBENCH_HOME"]) / "audits").exists()

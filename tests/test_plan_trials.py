"""scripts/plan_trials.py: how many trials a public test needs, against the exact figures in
docs/experiment-protocol.md, section 8."""
import contextlib
import importlib.util
import io
from pathlib import Path

import pytest

from briefbench.stats import sign_test

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("plan_trials", ROOT / "scripts" / "plan_trials.py")
plan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan)


def test_the_critical_values_are_the_sign_tests():
    """For each number of decided pairs, the most losses B can have and still win significantly, exactly as the
    bench's own sign test decides it."""
    limits = plan.most_losses(0.05, 200)
    for decided, most in enumerate(limits):
        assert most < 0 or sign_test(decided - most, most) <= 0.05
        more = most + 1
        assert not (decided - more > more and sign_test(decided - more, more) <= 0.05)
    assert limits[5] == -1 and limits[6] == 0              # 5 to 0 gives p = 0.0625, and 6 to 0 gives 0.031


@pytest.mark.parametrize("gain,q,trials", [(0.15, 0.15, 52), (0.15, 0.30, 112), (0.10, 0.20, 168),
                                           (0.20, 0.50, 103), (0.15, 0.35, 129)])
def test_trials_where_the_trick_should_help_match_the_protocol(gain, q, trials):
    found, chance = plan.help_trials(q - gain, gain, 0.80, 0.05)
    assert found == trials and chance >= 0.80


@pytest.mark.parametrize("noise,trials", [(0.0, 35), (0.02, 53), (0.05, 69)])
def test_trials_where_the_trick_could_hurt_match_the_protocol(noise, trials):
    assert plan.harm_trials(noise, 0.10, 0.80, 0.05)[0] == trials


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = plan.main(list(argv))
    return code, out.getvalue()


def test_a_calibration_with_room_gives_the_number_of_trials_and_runs():
    code, text = run("--failed", "16/40", "--disagreed", "4/20", "--harm-disagreed", "1/10")
    assert code == 0, text
    assert "the plain prompt failed 16 of 40 runs (40%, 95% interval 25% to 57%)" in text
    assert "129 trials give a chance of 80.3% to find a gain of 15 points" in text
    assert "100 trials give a chance of 81.7% to show \"no loss over 10 points\"" in text
    assert "In all: 229 trials, 458 runs." in text


def test_a_calibration_without_room_stops_before_any_plan():
    code, text = run("--failed", "3/40", "--disagreed", "2/20")
    assert code == 1 and "No room on these materials" in text and "trials give" not in text


def test_a_count_must_be_a_part_of_a_whole():
    with pytest.raises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
        run("--failed", "41/40", "--disagreed", "2/20")

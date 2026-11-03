"""The statistics, the judge's combining rule, and score's report on a fixture log, against hand-computed numbers."""
import json
from importlib import resources
from math import comb

import pytest

from briefbench import judge, score
from briefbench.experiment import RULE
from briefbench.stats import decide, interval, sign_test


def test_sign_test_and_interval_match_hand_computed_values():
    assert sign_test(16, 4) == pytest.approx(2 * (1 + 20 + 190 + 1140 + 4845) / 2 ** 20)    # 0.0118
    assert sign_test(4, 16) == sign_test(16, 4) and sign_test(10, 10) == 1.0 and sign_test(0, 0) == 1.0
    lo, hi = interval(16, 20)                                      # Clopper-Pearson tables: 0.5634 to 0.9427
    assert lo == pytest.approx(0.56339, abs=2e-5) and hi == pytest.approx(0.94266, abs=2e-5)
    assert interval(0, 10)[0] == 0.0 and interval(10, 10)[1] == 1.0 and interval(0, 0) == (0.0, 1.0)


@pytest.mark.parametrize("winners,trials,expected", [
    (["b"] * 15, 15, ("collecting", 15, 15)),
    (["b"] * 16 + ["a"] * 4, 20, ("adopt", 16, 20)),
    (["b"] * 16 + ["a"] * 4 + ["a"] * 30, 50, ("adopt", 16, 20)),          # the rule looks at the first 20 only
    (["b"] * 10 + ["a"] * 10, 20, ("stop", 10, 20)),
    (["b"] * 13 + ["a"] * 7, 20, ("continue", 13, 20)),
    (["b"] * 13 + ["a"] * 7 + ["b"] * 14 + ["a"] * 6, 40, ("adopt", 27, 40)),
    (["b"] * 13 + ["a"] * 7 + ["b"] * 13 + ["a"] * 7, 40, ("stop", 26, 40)),
    (["b"] * 19, 40, ("no-difference", 19, 19)),                            # fewer than 20 of 40 trials decided
])
def test_the_two_step_rule(winners, trials, expected):
    assert decide(winners, trials, RULE) == expected


@pytest.mark.parametrize("p,adopted", [(0.5, 0.0222), (0.65, 0.4482), (0.75, 0.8975)])
def test_the_rule_has_the_error_rates_the_design_states(p, adopted):
    """docs/design.md: wrongly adopts 2.2% of the time, catches 75% wins 90% and 65% wins 45% of the time."""
    def pmf(k):
        return comb(20, k) * p ** k * (1 - p) ** (20 - k)
    total = sum(pmf(x) * pmf(y) for x in range(21) for y in range(21)
                if decide(["b"] * x + ["a"] * (20 - x) + ["b"] * y + ["a"] * (20 - y), 40, RULE)[0] == "adopt")
    assert total == pytest.approx(adopted, abs=5e-4)


def test_the_judge_counts_a_win_only_when_both_orders_agree():
    sides = {"1": "SIDE-ONE", "2": "SIDE-TWO"}

    def judge_by(rule):
        def call(prompt):
            first = "1" if prompt.index("SIDE-ONE") < prompt.index("SIDE-TWO") else "2"
            return json.dumps({"goal_met": "g", "check_passed": "c", "verdict": rule(first)})
        return call

    assert judge.rule("goal", sides, judge_by(lambda first: "[[A>B]]" if first == "1" else "[[B>>A]]"))["winner"] == "1"
    flipped = judge.rule("goal", sides, judge_by(lambda first: "[[A>B]]"))      # always prefers what it sees first
    assert flipped["winner"] == "tie" and [o["verdict"] for o in flipped["orders"]] == ["[[A>B]]", "[[A>B]]"]
    assert judge.rule("goal", sides, judge_by(lambda first: "[[A=B]]"))["winner"] == "tie"
    assert judge.rule("  ", sides, None) == {"orders": [], "winner": None, "skipped": "no goal was given"}
    assert judge.rule("goal", {"1": "x" * 70_000, "2": "y"}, None)["skipped"].startswith("a side is over")
    with pytest.raises(ValueError):
        judge.rule("goal", sides, judge_by(lambda first: "A is better"))


def test_the_judge_prompt_is_the_adapted_one_with_its_license():
    text = judge.template()
    assert text.startswith("Please act as an impartial judge") and "Arena-Hard" not in text
    assert all(label in text for label in judge.LABELS) and "{goal}" in text and "{a}" in text and "{b}" in text
    folder = resources.files("briefbench")
    assert "Arena-Hard-Auto" in folder.joinpath("judge_prompt.md").read_text()
    assert "Apache License" in folder.joinpath("judge_prompt_license.txt").read_text()
    shown = judge.material("+fix\n", {"passed": False, "exit_code": 1}, "1 failed", False)
    assert "The check failed (exit 1)" in shown and "1 failed" in shown and "+fix" in shown


def trial(winner, by="you", *, seconds=(100, 110), tokens=(1000, 1200), sizes=None, judged=None, guess=None,
          kind="trial", experiment="fx"):
    sizes = sizes or ({"a": (200, 300), "b": (200, 300), "tie": (250, 250)}[winner])
    arms = {s: {"seconds": seconds[i], "tokens": tokens[i], "model": "m1", "diff": {"bytes": sizes[i]}}
            for i, s in enumerate("ab")}
    if winner == "a":                                   # in the fixture, A wins with the shorter diff
        arms["a"]["diff"]["bytes"], arms["b"]["diff"]["bytes"] = 100, 300
    return {"schema": 1, "kind": kind, "experiment": experiment, "arms": arms,
            "decision": {"by": by, "winner": winner, "sides": {"1": "b", "2": "a"}, "guess": guess},
            "judge": None if judged is None else {"winner": judged}}


def fixture_log():
    """23 trials: 16 B wins and 4 A wins (10 decided by the check, 10 by you) and 3 ties; 10 judged, 8 agreeing;
    6 guesses, 3 right; 3 noise checks, 1 with a winner; 2 exclusions; and lines of another experiment."""
    by = ["check"] * 8 + ["you"] * 8 + ["check"] * 2 + ["you"] * 2
    entries = [trial(w, b) for w, b in zip(["b"] * 16 + ["a"] * 4, by)]
    entries += [trial("tie") for _ in range(3)]
    you = [t for t in entries if t["decision"]["by"] == "you"]                 # 10 picks by you, then 3 ties
    for t, agrees in zip(you[:10], [True] * 8 + [False] * 2):
        t["judge"] = {"winner": t["decision"]["winner"] if agrees else ("a" if t["decision"]["winner"] == "b" else "b")}
    for t, guess in zip(you[:6], ["1", "1", "1", "2", "2", "2"]):             # side 1 is B, so "1" is right
        t["decision"]["guess"] = guess
    entries += [trial("tie", kind="aa"), trial("tie", kind="aa"), trial("a", kind="aa")]
    entries += [{"kind": "excluded", "experiment": "fx", "reasons": ["steered"]}] * 2
    entries += [trial("a", experiment="other")] * 5 + [{"kind": "rewrite"}]
    return entries


EXPERIMENT = {"name": "fx", "a": {"spec": "original"}, "b": {"spec": "brief"}, "rule": RULE, "cap_percent": 50,
              "worker": {"agent": "claude-code", "model": "m1"}, "judge": {"agent": "codex"}}


def test_score_matches_hand_computed_results_on_a_fixture_log():
    lines = score.report(EXPERIMENT, fixture_log()).splitlines()
    assert lines[1:] == [
        "Trials: 23. B won 16, A won 4, 3 ties.",
        "Sign test on 20 decided pairs: p = 0.0118; B's win rate 80%, 95% interval 56% to 94%.",
        "Verdict: adopt B. It won 16 of 20 decided pairs, which the rule fixed in advance accepts, and its extra "
        "cost is within your cap.",
        "Median extra cost of B over A: +10% time, +20% tokens (your cap: 50%).",
        "Judge agreed with your pick: 8 of 10 (80%); recorded only, until it agrees with 80% of 20 or more picks.",
        "The longer diff won 16 of 20 (80%) decided pairs with diffs of different sizes.",
        "Your guesses of which side got B: 3 of 6 (50%) right; about half means the blinding holds.",
        "Noise checks (A against A): 3, with a winner in 1; often a winner there means high noise.",
        "Excluded tasks: 2 of 25 considered.",
    ]


def test_a_win_over_the_cost_cap_is_not_adopted():
    text = score.report(EXPERIMENT | {"cap_percent": 15}, fixture_log())
    assert "but its median extra tokens is over your 15% cap, so it is not adopted." in text


def test_score_never_reports_a_few_pairs_as_evidence():
    text = score.report(EXPERIMENT | {"judge": None}, [trial("b", "check")])
    assert "Verdict: none yet. 1 of the 20 decided pairs" in text and "Judge: off." in text
